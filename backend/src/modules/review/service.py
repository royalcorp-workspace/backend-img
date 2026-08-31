from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceNotFoundError
from .crud import crud_reviews
from .schemas import ReviewCreate, ReviewUpdate

logger = get_logger()


class ReviewService:
    async def get_by_product_id(self, db: AsyncSession, product_id: UUID) -> dict[str, Any]:
        result = await crud_reviews.get_multi(
            db=db, product_id=product_id, deleted=False
        )
        reviews = result.get("data", [])
        avg_rating = (
            sum(r["rating"] for r in reviews if r.get("rating")) / len(reviews) if reviews else 0
        )
        return {
            "reviews": reviews,
            "avg_rating": round(avg_rating, 2),
            "total_reviews": len(reviews),
        }

    async def create(self, db: AsyncSession, review_in: ReviewCreate) -> dict[str, Any]:
        return await crud_reviews.create(db=db, object=review_in)

    async def update(self, db: AsyncSession, review_id: int, review_in: ReviewUpdate) -> dict[str, Any]:
        review = await crud_reviews.get(db=db, id=review_id, deleted=False)
        if not review:
            raise ResourceNotFoundError(f"Review with ID {review_id} not found")
        return await crud_reviews.update(db=db, object=review_in, id=review_id)

    async def delete(self, db: AsyncSession, review_id: int) -> None:
        review = await crud_reviews.get(db=db, id=review_id, deleted=False)
        if not review:
            raise ResourceNotFoundError(f"Review with ID {review_id} not found")
        await crud_reviews.delete(db=db, id=review_id)


review_service = ReviewService()
