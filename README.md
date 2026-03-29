# AI News Platform

A production-ready AI news platform with RAG-based Q&A chat, semantic search over 10k+ articles, and sub-second retrieval using FAISS.

Built with FastAPI, MySQL, OpenAI embeddings, and deployed on AWS EC2.

## Live Demo

- App: http://3.17.170.220/
- API Docs: http://3.17.170.220/docs
- Status: Live on AWS EC2

## Highlights

- Designed and deployed a production-ready RAG system with FAISS-based retrieval and GPT-4o-mini grounding
- Achieved sub-second semantic search over 10k+ articles using vector similarity (FAISS IndexFlatIP)
- Built async ingestion pipeline (RSS + NewsAPI) with scheduled jobs and automatic embedding updates
- Implemented fault-tolerant AI services with graceful degradation when OpenAI API fails
- Containerized with Docker Compose and deployed on AWS EC2 with Nginx reverse proxy

```
┌─────────────────────┐    HTTP/JSON    ┌──────────────────────────┐
│  news-frontend-ai   │ ◄─────────────► │  FastAPI + MySQL         │
│                     │                 │                          │
│  • Browse by topic  │  /api/ai/search │  OpenAI text-embedding   │
│  • Semantic search  │  /api/ai/related│  FAISS vector index      │
│  • Related articles │  /api/ai/chat   │  RSS + NewsAPI scraper   │
│  • AI Chat Widget   │                 │  GPT-4o-mini (RAG)       │
└─────────────────────┘                 └──────────────────────────┘
         │                                          │
         └──────────────── Nginx ───────────────────┘
                      (AWS EC2, Docker Compose)
```

## Performance

| Metric | Value |
|--------|-------|
| Semantic search latency | < 1s over 10,000+ articles |
| Embedding cost | ~$0.02 per 10k articles (`text-embedding-3-small`) |
| API response time | ~50ms (standard) / ~300ms (AI endpoints) |
| Scheduled ingestion | Twice daily, fully automated |

## Features

| Feature | Description |
|---------|-------------|
| **AI Chat (RAG)** | Ask questions in natural language — retrieves top-5 relevant articles via FAISS and feeds them to GPT-4o-mini for grounded answers |
| **Semantic Search** | Natural language search via OpenAI embeddings + FAISS — finds meaning, not just keywords |
| **Related Articles** | Per-article recommendations using cosine similarity on pre-computed embeddings |
| **News Scraping** | Auto-scrapes RSS feeds + NewsAPI on startup and refreshes content twice daily |
| **Auth** | Token-based authentication with session management |
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
| Infrastructure | Docker Compose, AWS EC2, Nginx |

## Quick Start

### Option A — Docker Compose (recommended)

```bash
git clone https://github.com/757019322/ai-news-platform.git
cd ai-news-platform

cp env.docker .env
# Edit .env with your OPENAI_API_KEY and NEWS_API_KEY
```

```bash
docker compose up --build -d
```

This starts two containers: `backend` (FastAPI on port 8000) and `db` (MySQL 8). On first startup the backend will:
1. Wait for MySQL to be ready, then run schema migrations
2. Scrape latest news from RSS feeds + NewsAPI
3. Embed all articles via OpenAI and build the FAISS index
4. Start the cron scheduler (refreshes content twice daily)

Interactive API docs: **http://localhost:8000/docs**

### Option B — Local (without Docker)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials

mysql -u root -p < database/database.sql

cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open `frontend/news-frontend-ai.html` directly in a browser for local development.

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_HOST` | ✓ | MySQL host (e.g. `localhost`) |
| `DB_PORT` | ✓ | MySQL port (default `3306`) |
| `DB_USER` | ✓ | MySQL username |
| `DB_PASSWORD` | ✓ | MySQL password |
| `DB_NAME` | ✓ | Database name (default `news_app`) |
| `OPENAI_API_KEY` | ✓ | OpenAI API key used for semantic embeddings |
| `NEWS_API_KEY` | optional | NewsAPI key for additional news sources (RSS still works without it) |
| `TOKEN_TTL_DAYS` | | Token expiry in days (default `7`) |
| `CORS_ORIGINS` | | Allowed origins, comma-separated (default `*`) |
| `DEBUG` | | Set `true` to expose error details in responses |

## AI Features

### Core System Design

The system implements a full RAG pipeline: ingestion → embedding → FAISS indexing → retrieval → grounded generation.

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

### AI Chat (RAG) — `POST /api/ai/chat`

Ask a question in natural language. The backend embeds the query, retrieves the top-5 most relevant articles from the FAISS index, and feeds them as context to GPT-4o-mini to produce a grounded answer.

```bash
curl -X POST "http://localhost:8000/api/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the latest developments in AI chips?"}'
```

```json
{
  "code": 200,
  "data": {
    "answer": "According to recent reports, NVIDIA announced its next-gen Blackwell architecture..."
  }
}
```

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

## Deployment

### Production (AWS EC2 + Docker Compose)

- **Instance**: t3.small, Ubuntu 24.04, Elastic IP `3.17.170.220`
- **Containers**: `docker compose up -d` — backend (FastAPI) + db (MySQL 8)
- **Frontend**: Static HTML served by Nginx
- **Reverse proxy**: Nginx routes `/api/*` → `localhost:8000`, `/` → frontend
- **Persistence**: MySQL data on EBS volume (expanded zero-downtime via `growpart` + `resize2fs`)
- **Auto-restart**: Docker `restart: always` policy keeps services up across reboots

## Project Structure

```
├── frontend/
│   └── news-frontend-ai.html       # Single-file SPA
├── backend/
│   ├── main.py                     # App entry point + lifespan
│   ├── config/db_conf.py           # DB session factory
│   ├── routers/
│   │   ├── ai.py                   # /api/ai/* — chat + search + related
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

Full spec: [`api-docs/api-spec.md`](api-docs/api-spec.md)  
Interactive (local): http://localhost:8000/docs  
Production: http://3.17.170.220/docs

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/ai/chat` | — | RAG-based Q&A chat |
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
