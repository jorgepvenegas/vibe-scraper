"""MongoDB connection manager using Motor (async driver)."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional


class MongoDB:
    """MongoDB connection manager using Motor."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls, connection_string: str, database_name: str):
        """Connect to MongoDB and test connection."""
        cls.client = AsyncIOMotorClient(connection_string)
        cls.db = cls.client[database_name]
        await cls.db.command("ping")

    @classmethod
    async def disconnect(cls):
        """Disconnect from MongoDB."""
        if cls.client:
            cls.client.close()

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if cls.db is None:
            raise RuntimeError("Database not connected")
        return cls.db

    @classmethod
    async def create_indexes(cls):
        """Create indexes for efficient queries."""
        scrapes = cls.db["scrapes"]

        await scrapes.create_index("scrape_id", unique=True)
        await scrapes.create_index([("request.url", 1), ("created_at", -1)])
        await scrapes.create_index("created_at")
        await scrapes.create_index("metadata.success")
        await scrapes.create_index("metadata.scrape_mode")
        await scrapes.create_index([
            ("metadata.success", 1),
            ("metadata.scrape_mode", 1),
            ("created_at", -1)
        ])
