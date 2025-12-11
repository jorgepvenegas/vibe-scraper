"""Routes for querying stored scrape history."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.database.mongodb import MongoDB
from src.models.schemas import ScrapeQueryResponse, StoredScrape
from src.repositories.scrape_repository import ScrapeRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrapes", tags=["Scrape History"])


def get_repository() -> ScrapeRepository:
    """Get repository instance.

    Returns:
        ScrapeRepository instance

    Raises:
        HTTPException: If database is not connected
    """
    try:
        db = MongoDB.get_database()
        return ScrapeRepository(db)
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available. Enable persistence and ensure MongoDB is running.",
        )


@router.get("/stats/summary")
async def get_scrape_statistics(
    from_date: datetime = Query(...), to_date: datetime = Query(...)
):
    """Get aggregate statistics for dashboard.

    Args:
        from_date: Start date for statistics
        to_date: End date for statistics

    Returns:
        Dictionary with aggregated statistics by mode and success status
    """
    repo = get_repository()
    stats = await repo.get_statistics(from_date, to_date)
    return {"statistics": stats}


@router.get("/", response_model=ScrapeQueryResponse)
async def query_scrapes(
    url: Optional[str] = None,
    mode: Optional[str] = None,
    success: Optional[bool] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
):
    """Query scrapes with various filters.

    Args:
        url: Filter by URL
        mode: Filter by scrape mode (static or dynamic)
        success: Filter by success status
        from_date: Filter scrapes from this date
        to_date: Filter scrapes until this date
        limit: Maximum number of results (max 100)
        offset: Number of results to skip

    Returns:
        ScrapeQueryResponse with matching results
    """
    repo = get_repository()

    # Build MongoDB query
    filters = {}
    if url:
        filters["request.url"] = url
    if mode:
        filters["metadata.scrape_mode"] = mode
    if success is not None:
        filters["metadata.success"] = success
    if from_date or to_date:
        filters["created_at"] = {}
        if from_date:
            filters["created_at"]["$gte"] = from_date
        if to_date:
            filters["created_at"]["$lte"] = to_date

    results = await repo.query(filters, limit=limit, skip=offset)

    # Get total count
    total = await repo.count(filters) if filters else 0

    # Convert results to StoredScrape instances for proper serialization
    stored_scrapes = [StoredScrape(**result) for result in results]

    return ScrapeQueryResponse(
        total=total, limit=limit, offset=offset, results=stored_scrapes
    )


@router.get("/{scrape_id}", response_model=StoredScrape)
async def get_scrape_by_id(scrape_id: str):
    """Get a specific scrape result by ID.

    Args:
        scrape_id: The scrape ID to retrieve

    Returns:
        The stored scrape document

    Raises:
        HTTPException: If scrape not found
    """
    repo = get_repository()
    result = await repo.get_by_id(scrape_id)

    if not result:
        raise HTTPException(status_code=404, detail="Scrape not found")

    # Convert to StoredScrape instance for proper serialization
    return StoredScrape(**result)
