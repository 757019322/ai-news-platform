from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from openai import AsyncOpenAI
from sqlalchemy import select, update

from config.db_conf import AsyncSessionLocal
from models.news import News

logger = logging.getLogger(__name__)

MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
DIMENSIONS = 1536
BATCH_SIZE = 256
FAISS_INDEX_PATH = Path(os.getenv("FAISS_INDEX_PATH", "faiss.index"))
FAISS_IDS_PATH = FAISS_INDEX_PATH.with_suffix(".ids.json")

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    response = await _get_client().embeddings.create(
        model=MODEL,
        input=[t.strip() for t in texts],
    )
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


async def embed_text(text: str) -> list[float]:
    results = await embed_texts([text])
    return results[0]


class EmbeddingIndex:
    def __init__(self) -> None:
        self._index = faiss.IndexHNSWFlat(DIMENSIONS, 32, faiss.METRIC_INNER_PRODUCT)
        self._ids: list[int] = []

    def _normalise(self, vec: list[float]) -> np.ndarray:
        arr = np.array(vec, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(arr)
        return arr

    def add(self, news_id: int, embedding: list[float]) -> None:
        self._index.add(self._normalise(embedding))
        self._ids.append(news_id)

    def search(self, query_embedding: list[float], k: int = 5) -> list[int]:
        if self._index.ntotal == 0:
            return []
        k = min(k, self._index.ntotal)
        scores, positions = self._index.search(self._normalise(query_embedding), k)
        return [
            self._ids[pos]
            for pos, score in zip(positions[0], scores[0])
            if pos >= 0 and score > 0
        ]

    @property
    def size(self) -> int:
        return self._index.ntotal

    def save(self) -> None:
        faiss.write_index(self._index, str(FAISS_INDEX_PATH))
        FAISS_IDS_PATH.write_text(json.dumps(self._ids))
        logger.info("FAISS index saved: %d articles.", self.size)

    @classmethod
    def load(cls) -> "EmbeddingIndex":
        instance = cls.__new__(cls)
        instance._index = faiss.read_index(str(FAISS_INDEX_PATH))
        instance._ids = json.loads(FAISS_IDS_PATH.read_text())
        logger.info("FAISS index loaded from disk: %d articles.", instance.size)
        return instance


_index = EmbeddingIndex()


def get_index() -> EmbeddingIndex:
    return _index


def _article_text(article: News) -> str:
    parts = [article.title]
    if article.description:
        parts.append(article.description)
    return " ".join(parts)


async def embed_all_news() -> None:
    global _index

    if FAISS_INDEX_PATH.exists() and FAISS_IDS_PATH.exists():
        try:
            _index = EmbeddingIndex.load()
        except Exception as exc:
            logger.warning("Failed to load FAISS index from disk, rebuilding: %s", exc)
            _index = EmbeddingIndex()

    async with AsyncSessionLocal() as db:
        stmt = select(News).where(News.embedding.is_(None))
        rows = (await db.execute(stmt)).scalars().all()

        if rows:
            logger.info("Embedding %d new articles in batches of %d...", len(rows), BATCH_SIZE)
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i : i + BATCH_SIZE]
                texts = [_article_text(a) for a in batch]
                try:
                    vectors = await embed_texts(texts)
                    for article, vec in zip(batch, vectors):
                        await db.execute(
                            update(News)
                            .where(News.id == article.id)
                            .values(embedding=json.dumps(vec))
                        )
                except Exception as exc:
                    logger.error(
                        "Batch embedding failed (articles %d-%d): %s",
                        i, i + len(batch), exc,
                    )
            await db.commit()
            logger.info("Embedding complete.")

        stmt = select(News.id, News.embedding).where(News.embedding.isnot(None))
        all_rows = (await db.execute(stmt)).all()

        _index = EmbeddingIndex()
        for row in all_rows:
            try:
                _index.add(row.id, json.loads(row.embedding))
            except Exception as exc:
                logger.warning("Skipped article %d from index: %s", row.id, exc)

        try:
            _index.save()
        except Exception as exc:
            logger.warning("Failed to persist FAISS index: %s", exc)

        logger.info("FAISS index built: %d articles indexed.", _index.size)
