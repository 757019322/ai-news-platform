# AI News Platform

A full-stack news platform with AI-powered semantic search and article recommendations. Built with FastAPI, MySQL, OpenAI embeddings, and FAISS.

```
┌─────────────────────┐    HTTP/JSON    ┌──────────────────────────┐
│  news-frontend-ai   │ ◄─────────────► │  FastAPI + MySQL         │
│                     │                 │                          │
│  • Browse by topic  │  /api/ai/search │  OpenAI text-embedding   │
│  • Semantic search  │  /api/ai/related│  FAISS vector index      │
│  • Related articles │                 │  RSS + NewsAPI scraper   │
└─────────────────────┘                 └──────────────────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| **Semantic Search** | Natural language search via OpenAI embeddings + FAISS — finds meaning, not just keywords |
| **Related Articles** | Per-article recommendations using cosine similarity on pre-computed embeddings |
| **News Scraping** | Auto-scrapes RSS feeds (TechCrunch, Wired, Ars Technica, The Verge) + NewsAPI on startup and every 6 hours |
| **Auth** | Token-based auth, SHA-256 hashed, server-side logout |
| **Favorites & History** | Save articles, track reading history per user |
| **Graceful Degradation** | AI features fail silently — server always starts, falls back to category-based results |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5 / CSS3 / Vanilla JS (single file, no build step) |
| Backend | Python 3.10+, FastAPI, async SQLAlchemy |
| Database | MySQL 8+ |
| AI / Search | OpenAI `text-embedding-3-small` + FAISS `IndexFlatIP` |
| Scraping | feedparser (RSS) + NewsAPI + APScheduler |
| Auth | Bearer token, SHA-256 hashed, TTL expiry |

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/757019322/ai-news-platform.git
cd ai-news-platform

cp backend/.env.example backend/.env
# Edit backend/.env with your credentials
```

### 2. Create the database

```bash
mysql -u root -p < database/database.sql
```

### 3. Install dependencies and run

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

On startup the server will:
1. Scrape latest tech news from RSS + NewsAPI
2. Embed all articles via OpenAI and build the FAISS index
3. Start the cron scheduler (re-scrapes at 06:00 and 18:00 UTC)

### 4. Open the frontend

Open `frontend/news-frontend-ai.html` directly in a browser — no build step needed.

Interactive API docs: **http://localhost:8000/docs**

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_HOST` | ✓ | MySQL host (e.g. `localhost`) |
| `DB_PORT` | ✓ | MySQL port (default `3306`) |
| `DB_USER` | ✓ | MySQL username |
| `DB_PASSWORD` | ✓ | MySQL password |
| `DB_NAME` | ✓ | Database name (default `news_app`) |
| `OPENAI_API_KEY` | ✓ | OpenAI key — [get one free](https://platform.openai.com) |
| `NEWS_API_KEY` | optional | NewsAPI key — [get one free](https://newsapi.org). Scraper still works via RSS if unset |
| `TOKEN_TTL_DAYS` | | Token expiry in days (default `7`) |
| `CORS_ORIGINS` | | Allowed origins, comma-separated (default `*`) |
| `DEBUG` | | Set `true` to expose error details in responses |

## AI Features

### Semantic Search — `GET /api/ai/search?q=...`

Converts the query to a 1536-dim embedding using `text-embedding-3-small`, then finds the nearest articles in the FAISS index using cosine similarity. No keyword matching — understands meaning.

```bash
curl "http://localhost:8000/api/ai/search?q=machine+learning+applications&limit=5"
```

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "id": 42,
        "title": "How AI Is Reshaping the Workplace",
        "description": "...",
        "publishTime": "2026-02-28T14:00:00",
        "categoryId": 1,
        "views": 12
      }
    ],
    "total": 5,
    "query": "machine learning applications"
  }
}
```

### Related Articles — `GET /api/ai/related?newsId=...`

Uses the article's stored embedding as a query vector. Falls back to same-category articles if the embedding isn't ready yet.

```bash
curl "http://localhost:8000/api/ai/related?newsId=42&limit=5"
```

### Embedding Pipeline

```
Article scraped
      │
      ▼
embed_all_news() on startup
      │
      ├─ SELECT articles WHERE embedding IS NULL
      ├─ OpenAI API → 1536-dim float vector
      ├─ Store as JSON string in news.embedding (MEDIUMTEXT)
      │
      ▼
Rebuild FAISS IndexFlatIP
      │
      ├─ L2-normalize all vectors
      └─ Inner product == cosine similarity
```

Cost: `text-embedding-3-small` ≈ $0.02 per 1M tokens. Embedding 10,000 articles costs ~$0.02 total.

## Project Structure

```
├── frontend/
│   └── news-frontend-ai.html       # Single-file SPA
├── backend/
│   ├── main.py                     # App entry point + lifespan
│   ├── config/db_conf.py           # DB session factory
│   ├── routers/
│   │   ├── ai.py                   # /api/ai/* — search + related
│   │   ├── news.py                 # /api/news/*
│   │   ├── users.py                # /api/user/*
│   │   ├── favorite.py             # /api/favorite/*
│   │   └── history.py              # /api/history/*
│   ├── services/
│   │   └── embedding.py            # OpenAI client + FAISS index
│   ├── crud/                       # DB query logic
│   ├── models/                     # SQLAlchemy ORM models
│   ├── schemas/                    # Pydantic schemas
│   ├── scraper/                    # RSS + NewsAPI + scheduler
│   ├── utils/                      # Auth, exceptions, response
│   ├── requirements.txt
│   └── .env.example
├── database/
│   └── database.sql                # Schema (run once to set up)
├── api-docs/
│   └── api-spec.md
├── backend-design.md
└── README.md
```

## API Reference

Full spec: [`api-docs/api-spec.md`](api-docs/api-spec.md) | Interactive: http://localhost:8000/docs

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/ai/search?q=` | — | Semantic search |
| GET | `/api/ai/related?newsId=` | — | Related articles |
| GET | `/api/news/categories` | — | List categories |
| GET | `/api/news/list?categoryId=` | — | Paginated news |
| GET | `/api/news/detail?id=` | — | Article detail + view count |
| POST | `/api/user/register` | — | Register |
| POST | `/api/user/login` | — | Login |
| GET | `/api/user/info` | ✓ | Profile |
| PUT | `/api/user/update` | ✓ | Update profile |
| PUT | `/api/user/password` | ✓ | Change password |
| POST | `/api/user/logout` | ✓ | Logout |
| POST | `/api/favorite/add` | ✓ | Add favorite |
| DELETE | `/api/favorite/remove` | ✓ | Remove favorite |
| GET | `/api/favorite/list` | ✓ | List favorites |
| POST | `/api/history/add` | ✓ | Record view |
| GET | `/api/history/list` | ✓ | View history |
| DELETE | `/api/history/clear` | ✓ | Clear history |
| GET | `/health` | — | Health check |
| POST | `/admin/scrape` | `X-Admin-Secret` | Trigger manual scrape |
