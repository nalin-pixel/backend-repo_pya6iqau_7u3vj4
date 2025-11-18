from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "appdb")

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(DATABASE_URL)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()[DATABASE_NAME]
    return _db

# Exported handle for convenience
db: AsyncIOMotorDatabase = get_db()


async def create_document(collection_name: str, data: Dict[str, Any]) -> str:
    doc = {
        **data,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await db[collection_name].insert_one(doc)
    return str(result.inserted_id)


async def get_documents(
    collection_name: str,
    filter_dict: Optional[Dict[str, Any]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    cursor = db[collection_name].find(filter_dict or {}).limit(limit)
    docs: List[Dict[str, Any]] = []
    async for d in cursor:
        d["_id"] = str(d["_id"])  # stringify for JSON safety
        docs.append(d)
    return docs
