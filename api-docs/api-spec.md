# AI News Platform API Specification

REST API specification for the AI News Platform. This document covers all endpoints consumed by the frontend (`frontend/news-frontend-ai.html`) and available for external integrations.

## Base URL

```
http://localhost:8000
```

## Authentication

Most endpoints require an `Authorization` header:

```
Authorization: Bearer <token>
```

Tokens are obtained via the Register or Login endpoints and stored client-side in `localStorage`. The backend validates tokens against the `user_token` table (SHA-256 hashed) with TTL-based expiration.

## Response Envelope

All endpoints return JSON in a consistent structure:

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

The frontend checks `code === 200` to determine success. Non-200 codes indicate errors, with a human-readable `message` field.

## Error Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid input, duplicate resource, incorrect password |
| 401 | Unauthorized | Missing, invalid, or expired token |
| 404 | Not Found | Resource does not exist |
| 422 | Validation Error | Request body fails Pydantic validation (e.g., username too short, missing required field) |
| 500 | Server Error | Unexpected failure (details only in DEBUG mode) |

All error responses use the same envelope format:

```json
{
  "code": 400,
  "message": "User already exists.",
  "data": null
}
```

---

## Users — `/api/user`

### Register

- **POST** `/api/user/register`
- **Auth**: not required
- **Request body**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| username | string | yes | Unique, 3–50 characters |
| password | string | yes | 6–128 characters |

- **Success response** (`data`):

```json
{
  "token": "abc123...",
  "userInfo": {
    "id": 1,
    "username": "john",
    "nickname": null,
    "avatar": null,
    "gender": "unknown",
    "bio": null,
    "phone": null
  }
}
```

- **Error cases**: 400 if username already exists, 422 if username < 3 chars or password < 6 chars.
- **Frontend usage**: Called from the Register tab in the auth panel. On success, stores token and userInfo in `localStorage`, updates the auth button text, and closes the panel.

### Login

- **POST** `/api/user/login`
- **Auth**: not required
- **Request body**: Same as Register
- **Success response**: Same structure as Register
- **Error cases**: 401 if username or password is wrong.
- **Frontend usage**: Called from the Sign In tab. Same post-login behavior as Register.

### Get Current User

- **GET** `/api/user/info`
- **Auth**: required
- **Success response** (`data`): `userInfo` object (same shape as above)
- **Frontend usage**: Called when the Profile sub-page opens to fetch fresh profile data from the server.

### Update Profile

- **PUT** `/api/user/update`
- **Auth**: required
- **Request body** (all fields optional):

| Field | Type | Notes |
|-------|------|-------|
| nickname | string | Display name (max 50) |
| avatar | string | Avatar URL (max 255) |
| gender | string | `"male"`, `"female"`, or `"unknown"` |
| bio | string | Short biography (max 500) |
| phone | string | Phone number (max 20) |

- **Success response** (`data`): Updated `userInfo` object
- **Error cases**: 422 if gender value is invalid.
- **Frontend usage**: Called from the Profile form's "Save Changes" button. The frontend currently sends `nickname`, `bio`, and `gender`.

### Change Password

- **PUT** `/api/user/password`
- **Auth**: required
- **Request body**:

| Field | Type | Required |
|-------|------|----------|
| oldPassword | string | yes |
| newPassword | string | yes (min 6 chars) |

- **Success response**: Standard envelope with `code: 200`
- **Error cases**: 400 if old password is incorrect, 422 if new password < 6 chars.
- **Frontend usage**: Called from the Profile form's "Update Password" button.

### Logout

- **POST** `/api/user/logout`
- **Auth**: required
- **Success response**: Standard envelope with `code: 200`
- **Frontend usage**: Called when the user clicks "Sign Out". Invalidates the token server-side, then the frontend clears `localStorage`.

---

## News — `/api/news`

### List Categories

- **GET** `/api/news/categories`
- **Auth**: not required
- **Success response** (`data`): Array of category objects (sorted by `sort_order`)

```json
[
  { "id": 1, "name": "Technology" },
  { "id": 2, "name": "Business" }
]
```

- **Frontend usage**: Called on page load to populate the category tab strip. The first category is auto-selected.

### List News

- **GET** `/api/news/list`
- **Auth**: not required
- **Query parameters**:

| Param | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| categoryId | int | yes | — | Filter by category |
| page | int | no | 1 | Page number (must be ≥ 1) |
| pageSize | int | no | 10 | Items per page (max 100) |

- **Success response** (`data`):

```json
{
  "list": [
    {
      "id": 1,
      "title": "Article Title",
      "description": "Short summary...",
      "image": "https://...",
      "author": "Reporter Name",
      "publishTime": "2025-01-15T10:30:00",
      "categoryId": 1,
      "views": 1234
    }
  ],
  "total": 42,
  "hasMore": true
}
```

- **Error cases**: 400 if page < 1.
- **Frontend usage**: Called on category selection and page change. Uses `pageSize=9`. The first item renders as a hero card; remaining items render in a card grid. `total` drives pagination.

### Get News Detail

- **GET** `/api/news/detail`
- **Auth**: not required
- **Query parameters**:

| Param | Type | Required |
|-------|------|----------|
| id | int | yes |

- **Success response** (`data`):

```json
{
  "id": 1,
  "title": "Article Title",
  "description": "Summary...",
  "content": "<p>Full HTML content...</p>",
  "image": "https://...",
  "author": "Reporter Name",
  "publishTime": "2025-01-15T10:30:00",
  "categoryId": 1,
  "views": 1235,
  "relatedNews": [
    { "id": 5, "title": "Related Article", "image": "https://..." }
  ]
}
```

- **Notes**: View count is incremented server-side on this call; the returned `views` reflects the post-increment count. `relatedNews` contains up to 5 other articles in the same category (only `id`, `title`, `image`).
- **Error cases**: 404 if news item does not exist.
- **Frontend usage**: Called when a news card or hero is clicked. Opens the article modal. The `content` field (HTML) is parsed and displayed as paragraphs. `relatedNews` renders at the bottom of the modal (up to 3 items).

---

## Favorites — `/api/favorite`

### Check Favorite Status

- **GET** `/api/favorite/check`
- **Auth**: required
- **Query parameters**: `newsId` (int)
- **Success response** (`data`):

```json
{ "isFavorite": true }
```

- **Frontend usage**: Called when opening an article modal (if logged in) to set the initial state of the favorite button.

### Add Favorite

- **POST** `/api/favorite/add`
- **Auth**: required
- **Request body**:

```json
{ "newsId": 123 }
```

- **Success response**: Standard envelope
- **Error cases**: 400 if already favorited.
- **Frontend usage**: Called when clicking the "♡ SAVE STORY" button in the article modal.

### Remove Favorite

- **DELETE** `/api/favorite/remove`
- **Auth**: required
- **Query parameters**: `newsId` (int)
- **Success response**: Standard envelope
- **Error cases**: 404 if favorite not found.
- **Frontend usage**: Called from two places — the "♥ SAVED" toggle in the article modal, and the remove (♥) button on each row in the Saved Stories list.

### List Favorites

- **GET** `/api/favorite/list`
- **Auth**: required
- **Query parameters**:

| Param | Type | Default |
|-------|------|---------|\
| page | int | 1 |
| pageSize | int | 10 |

- **Success response** (`data`):

```json
{
  "list": [
    {
      "id": 1,
      "favoriteId": 42,
      "title": "Article Title",
      "image": "https://...",
      "favoriteTime": "2025-01-16T09:00:00",
      "categoryId": 1,
      "views": 100
    }
  ],
  "total": 5,
  "hasMore": false
}
```

- **Frontend usage**: Called when opening the Saved Stories sub-page (requests `pageSize=20`). Also called with `pageSize=1` on panel open to get the `total` count for the stats row.

---

## History — `/api/history`

### Add History Record

- **POST** `/api/history/add`
- **Auth**: required
- **Request body**:

```json
{ "newsId": 123 }
```

- **Success response**: Standard envelope
- **Notes**: If the user has already viewed this article, the existing record's `view_time` is updated rather than creating a duplicate.
- **Frontend usage**: Called automatically (fire-and-forget, errors silenced) when an article modal opens for a logged-in user.

### List History

- **GET** `/api/history/list`
- **Auth**: required
- **Query parameters**:

| Param | Type | Default |
|-------|------|---------|\
| page | int | 1 |
| pageSize | int | 10 |

- **Success response** (`data`):

```json
{
  "list": [
    {
      "id": 1,
      "historyId": 7,
      "title": "Article Title",
      "image": "https://...",
      "viewTime": "2025-01-16T08:30:00",
      "categoryId": 1,
      "views": 50
    }
  ],
  "total": 15,
  "hasMore": true
}
```

- **Frontend usage**: Called when opening the Reading History sub-page (requests `pageSize=10`). Also called with `pageSize=1` on panel open for the stats row count.

### Clear History

- **DELETE** `/api/history/clear`
- **Auth**: required
- **Success response**: Standard envelope
- **Frontend usage**: Not currently wired in the frontend UI, but available via API.

---

## Admin / Utility

### Health Check

- **GET** `/health`
- **Response**: `{ "status": "ok" }`

### Trigger Scrape

- **POST** `/admin/scrape`
- **Auth**: `X-Admin-Secret` header required (must match `ADMIN_SECRET` env var)
- **Response**: `{ "status": "ok", "message": "Scrape and embedding complete." }`
- **Notes**: Manually triggers news scraping. The scraper also runs automatically on startup and on a cron schedule (06:00 and 18:00 UTC).

---

## AI — `/api/ai`

Both endpoints share the same FAISS vector index and OpenAI embedding pipeline. The index is built on startup and updated after each scrape. No auth is required.

### Semantic Search

- **GET** `/api/ai/search`
- **Auth**: not required
- **Query parameters**:

| Param | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| q | string | yes | — | Natural language search query (min 1 char) |
| limit | int | no | 10 | Max results (1–50) |

- **Success response** (`data`):

```json
{
  "list": [
    {
      "id": 178,
      "title": "Are You 'Agentic' Enough for the AI Era?",
      "description": "Silicon Valley built AI coding agents...",
      "image": "https://...",
      "author": "Maxwell Zeff",
      "categoryId": 7,
      "views": 0,
      "publishTime": "2026-02-26T19:00:00"
    }
  ],
  "total": 10,
  "query": "artificial intelligence productivity"
}
```

- **Notes**: Results are ranked by cosine similarity between the query embedding and article embeddings. Returns `{ list: [], total: 0 }` with message `"Search index not ready yet."` if the FAISS index has not been built. Returns 503 if the OpenAI API call fails.
- **Frontend usage**: Called when the user submits a search query via the search bar. Results replace the normal category browse view. The first result renders as a hero card.

### Related Articles

- **GET** `/api/ai/related`
- **Auth**: not required
- **Query parameters**:

| Param | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| newsId | int | yes | — | ID of the source article |
| limit | int | no | 5 | Max results (1–20) |

- **Success response** (`data`):

```json
{
  "list": [
    {
      "id": 134,
      "title": "Top 10 AI Tools in 2023",
      "description": "...",
      "image": "https://...",
      "author": "Unknown",
      "categoryId": 7,
      "views": 0,
      "publishTime": "2023-01-25T19:52:00"
    }
  ],
  "total": 4
}
```

- **Notes**: Uses the source article's pre-computed embedding to query FAISS. The source article itself is excluded from results. If the article does not yet have an embedding (e.g., just scraped), falls back to the most recent articles in the same category; the response message will be `"Related articles fetched (category fallback)."`.
- **Error cases**: 404 if the article does not exist. 500 if stored embedding data is corrupt.
- **Frontend usage**: Called when an article modal opens, replacing the static `relatedNews` from the detail endpoint. Displays up to 4 related articles at the bottom of the modal.
