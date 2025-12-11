"""Repository for scrape results CRUD operations."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase


class ScrapeRepository:
    """Repository for scrape results CRUD operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize repository with database connection."""
        self.collection = db["scrapes"]

    async def create(self, scrape_document: dict) -> str:
        """Insert new scrape result.

        Args:
            scrape_document: Document to insert

        Returns:
            The scrape_id of the created document
        """
        scrape_document["scrape_id"] = str(uuid4())
        scrape_document["created_at"] = datetime.utcnow()
        scrape_document["updated_at"] = datetime.utcnow()

        await self.collection.insert_one(scrape_document)
        return scrape_document["scrape_id"]

    async def get_by_id(self, scrape_id: str) -> Optional[dict]:
        """Get scrape by ID.

        Args:
            scrape_id: The scrape ID to look up

        Returns:
            The scrape document or None if not found
        """
        return await self.collection.find_one(
            {"scrape_id": scrape_id},
            {"_id": 0}
        )

    async def get_by_url(
        self,
        url: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[dict]:
        """Get scrapes by URL.

        Args:
            url: The URL to search for
            limit: Maximum number of results
            skip: Number of results to skip

        Returns:
            List of scrape documents
        """
        cursor = self.collection.find(
            {"request.url": url},
            {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit)

        return await cursor.to_list(length=limit)

    async def query(
        self,
        filters: dict,
        limit: int = 50,
        skip: int = 0,
        sort_by: str = "created_at",
        sort_order: int = -1
    ) -> List[dict]:
        """Query scrapes with filters.

        Args:
            filters: MongoDB filter dictionary
            limit: Maximum number of results
            skip: Number of results to skip
            sort_by: Field to sort by
            sort_order: 1 for ascending, -1 for descending

        Returns:
            List of scrape documents
        """
        cursor = self.collection.find(
            filters,
            {"_id": 0}
        ).sort(sort_by, sort_order).skip(skip).limit(limit)

        return await cursor.to_list(length=limit)

    async def count(self, filters: dict) -> int:
        """Count documents matching filters.

        Args:
            filters: MongoDB filter dictionary

        Returns:
            Number of matching documents
        """
        return await self.collection.count_documents(filters)

    async def get_statistics(
        self,
        from_date: datetime,
        to_date: datetime
    ) -> List[dict]:
        """Get aggregated statistics for dashboard.

        Args:
            from_date: Start date for statistics
            to_date: End date for statistics

        Returns:
            List of aggregated statistics
        """
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": from_date, "$lte": to_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "mode": "$metadata.scrape_mode",
                        "success": "$metadata.success"
                    },
                    "count": {"$sum": 1},
                    "avg_duration": {"$avg": "$metadata.duration_ms"}
                }
            }
        ]

        return await self.collection.aggregate(pipeline).to_list(None)
