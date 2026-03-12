# Backend Design — AI News Platform

## Overview

A FastAPI REST backend with AI-powered semantic search. Handles news scraping, embedding generation, vector search, user auth, favorites, and reading history.

## System Architecture

```
┌──────────────────────┐     HTTP/JSON      ┌─────────────────────────────────┐
│  news-frontend-ai    │ ◄────────────────► │         FastAPI Backend         │
│  .html               │                    │                                 │
│                      │  /api/ai/search    │  routers/ ──► crud/             │
│  • Browse news       │  /api/ai/related   │      │            │             │
│  • Semantic search   │  /api/news/*       │  schemas/      models/          │
│  • Auth / profile    │  /api/user/*       │      │            │             │
│  • Favorites         │  /api/favorite/*   │  utils/        config/          │
│  • History           │  /api/history/*    │                                 │
└──────────────────────┘                    │  services/embedding.py          │
                                            │      │                          │
                                            │      ├─ OpenAI API              │
                                            │      └─ FAISS index (memory)    │
                                            │                                 │
                                            │  scraper/ ──► RSS / NewsAPI     │
                                            └──────────────┬──────────────────┘
                                                           │
                                                  ┌────────▼────────┐
                                                  │    MySQL 8+     │
                                                  │                 │
                                                  │  user           │
                                                  │  user_token     │
                                                  │  news_category  │
                                                  │  news           │
                                                  │  favorite       │
                                                  │  history        │
                                                  └─────────────────┘
```

## Data Flow

### Read path (browse / search)
```
Client GET /api/news/list
  → router validates query params
  → crud.get_news_list() — SELECT ... ORDER BY publish_time DESC
  → router serializes and returns JSON envelope
```

### Write path (favorite / history)
```
Client POST /api/favorite/add
  → get_current_user() resolves Bearer token → User row
  → crud.add_favorite() — INSERT + flush (no commit yet)
  → router calls db.commit()
  → success_response()
  → on exception: get_db() rolls back automatically
```

### AI search path
```
Client GET /api/ai/search?q=...
  → embed_text(q) — OpenAI API → 1536-dim float vector
  → EmbeddingIndex.search(vec, k=limit) — FAISS inner product search
  → _fetch_articles(db, ids) — SELECT WHERE id IN (...), reorder by FAISS rank
  → serialize and return
```

## Layer Responsibilities

| Layer | Responsibility |
|-------|----------------|
| `routers/` | HTTP in/out, auth dependency injection, `db.commit()` |
| `services/` | Business logic spanning multiple models (embedding pipeline) |
| `crud/` | SQL queries only — always `flush()`, never `commit()` |
| `models/` | SQLAlchemy ORM table definitions |
| `schemas/` | Pydantic validation + camelCase serialization |
| `utils/` | Auth resolution, exception handlers, response envelope |
| `scraper/` | RSS + NewsAPI fetch, dedup, insert |
| `config/` | Engine + session factory |

## Session & Transaction Management

`get_db()` provides a session with no auto-commit. The router owns the transaction boundary.

```
request arrives
  │
  ├─ get_db() opens AsyncSession
  │
  ├─ CRUD calls flush() — writes staged, not committed
  │
  ├─ router calls db.commit() — single commit per request
  │
  └─ on any exception → get_db() rolls back
```

This ensures exactly one commit per request and prevents partial writes from being silently persisted.

## AI — Semantic Search Pipeline

### Embedding generation (startup + post-scrape)

```
embed_all_news()
  │
  ├─ SELECT news WHERE embedding IS NULL
  │
  ├─ for each article:
  │     text = title + " " + description
  │     vec  = OpenAI text-embedding-3-small(text)  → list[float] × 1536
  │     UPDATE news SET embedding = json.dumps(vec)
  │
  ├─ db.commit()
  │
  └─ rebuild FAISS index:
        _index = EmbeddingIndex()
        for each (id, embedding) in DB:
            _index.add(id, json.loads(embedding))
```

### FAISS Index Design

```
Index type:  IndexFlatIP  (exact inner product, no approximation)
Dimensions:  1536         (text-embedding-3-small output size)
Normalization: L2-normalize every vector before add/search
               → inner product == cosine similarity

Why IndexFlatIP over IndexFlatL2?
  Cosine similarity is the standard metric for text embeddings.
  After L2 normalization, inner product is identical to cosine,
  so IndexFlatIP gives us cosine search without extra steps.

Persistence:
  Index is rebuilt from MySQL on every startup.
  No index file to manage — stateless, easy to redeploy.
```

### Degradation Strategy

| Situation | Behavior |
|-----------|----------|
| `OPENAI_API_KEY` not set | `embed_all_news()` raises, caught in lifespan — server starts with empty index |
| FAISS index empty (0 articles) | `/api/ai/search` returns `{ list: [], total: 0 }` with message "Search index not ready yet." |
| Article has no embedding | `/api/ai/related` falls back to most recent articles in same category |
| OpenAI API call fails at search time | Returns HTTP 503 "Search service unavailable." |
| Any startup step fails | Logged as non-fatal error, next step continues, API always starts |

## Authentication

```
POST /api/user/login
  │
  ├─ verify bcrypt(password, stored_hash)
  ├─ generate uuid4() raw token
  ├─ store SHA-256(raw_token) in user_token table with TTL
  └─ return raw token to client

Subsequent requests:
  Authorization: Bearer <raw_token>
  │
  ├─ hash incoming token → lookup user_token by hash
  ├─ check expires_at > now()
  └─ return User row to endpoint via Depends(get_current_user)

Logout: DELETE user_token row → token immediately invalid server-side
```

Raw token is never stored. Only the SHA-256 hash is persisted, so a DB leak does not expose usable tokens.

## News Scraping

```
run_scraper()
  │
  ├─ one top-level transaction (db.begin())
  │
  └─ for each category in RSS_SOURCES:
        fetch_newsapi(category)    → list[dict]
        fetch_rss(url) × N        → list[dict]
        │
        └─ _insert_articles():
              for each article:
                SELECT id WHERE title = ? AND category_id = ?
                if exists → skip
                else:
                  BEGIN SAVEPOINT
                    INSERT news row
                    flush()
                  RELEASE SAVEPOINT   ← success
                  or ROLLBACK SAVEPOINT ← IntegrityError on this row only,
                                          rest of batch continues
```

SAVEPOINTs ensure a duplicate on one article does not abort the entire batch.

## Error Handling

All responses use `{ code, message, data }`. Global handlers registered in `utils/exception_handlers.py`:

| Exception | HTTP | Message |
|-----------|------|---------|
| `RequestValidationError` | 422 | First field + Pydantic message |
| `HTTPException` | varies | `exc.detail` |
| `IntegrityError` | 400 | Mapped from constraint name (username_UNIQUE, uniq_user_news, etc.) |
| `SQLAlchemyError` | 500 | "Database operation failed." |
| `Exception` | 500 | "Internal server error." |

Raw details (traceback, SQL) only exposed when `DEBUG=true`.

## API Surface

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/ai/search` | — | Semantic search via FAISS + OpenAI |
| GET | `/api/ai/related` | — | Related articles via embedding similarity |
| GET | `/api/news/categories` | — | List categories |
| GET | `/api/news/list` | — | Paginated news by category |
| GET | `/api/news/detail` | — | Article + view increment |
| POST | `/api/user/register` | — | Register |
| POST | `/api/user/login` | — | Login, get token |
| GET | `/api/user/info` | ✓ | Current user profile |
| PUT | `/api/user/update` | ✓ | Update profile |
| PUT | `/api/user/password` | ✓ | Change password |
| POST | `/api/user/logout` | ✓ | Invalidate token |
| GET | `/api/favorite/check` | ✓ | Is article favorited? |
| POST | `/api/favorite/add` | ✓ | Add favorite |
| DELETE | `/api/favorite/remove` | ✓ | Remove favorite |
| GET | `/api/favorite/list` | ✓ | List favorites |
| POST | `/api/history/add` | ✓ | Record view |
| GET | `/api/history/list` | ✓ | List history |
| DELETE | `/api/history/clear` | ✓ | Clear history |
| GET | `/health` | — | Health check |
| POST | `/admin/scrape` | `X-Admin-Secret` | Trigger scrape + re-embed |

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | MySQL host | `localhost` |
| `DB_PORT` | MySQL port | `3306` |
| `DB_USER` | MySQL user | `root` |
| `DB_PASSWORD` | MySQL password | — |
| `DB_NAME` | Database name | `news_app` |
| `OPENAI_API_KEY` | OpenAI key (AI features disabled if unset) | — |
| `NEWS_API_KEY` | NewsAPI key (RSS still works if unset) | — |
| `TOKEN_TTL_DAYS` | Token TTL | `7` |
| `CORS_ORIGINS` | Allowed origins | `*` |
| `DEBUG` | Expose error details | `false` |
| `SQLALCHEMY_ECHO` | Log SQL | `false` |
| `DB_POOL_SIZE` | Connection pool | `10` |
| `DB_MAX_OVERFLOW` | Overflow connections | `20` |
