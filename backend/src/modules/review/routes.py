from typing import Annotated, Any

from fastapi import APIRouter, Depends

from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from .dependencies import ReviewServiceDep
from .schemas import ProductReviewsRead, ReviewCreate, ReviewRead, ReviewUpdate

router = APIRouter(tags=["Reviews"])


@router.get(
    "/products/{product_id}",
    response_model=ProductReviewsRead,
    responses={
        200: {
            "description": "Product reviews",
            "content": {"application/json": {"example": {"reviews": [], "avg_rating": 0.0, "total_reviews": 0}}},
        },
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Product not found",
            "content": {"application/json": {"example": {"detail": "Product not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def list_reviews_by_product(
    product_id: int,
    db: AsyncSessionDep,
    review_service: ReviewServiceDep,
) -> Any:
    return await review_service.get_by_product_id(db, product_id)


@router.post(
    "/products/{product_id}",
    response_model=ReviewRead,
    status_code=201,
    responses={
        201: {
            "description": "Review created",
            "content": {
                "application/json": {
                    "example": {
                        "product_id": 1,
                        "order_id": 1,
                        "user_name": "John Doe",
                        "user_email": "john@example.com",
                        "rating": 5,
                        "text": "Great product!",
                        "image_url": None,
                        "is_approved": False,
                        "is_published": False,
                        "report_count": 0,
                        "id": 1,
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00",
                    }
                }
            },
        },
        400: {
            "description": "Invalid data",
            "content": {"application/json": {"example": {"detail": "Invalid data", "support_id": "a1b2c3d4"}}},
        },
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def create_review(
    product_id: int,
    review_in: ReviewCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("reviews:create"))],
    review_service: ReviewServiceDep,
) -> dict[str, Any]:
    review_in.product_id = product_id
    return await review_service.create(review_in, db)


@router.put(
    "/{review_id}",
    response_model=ReviewRead,
    responses={
        200: {
            "description": "Review updated",
            "content": {
                "application/json": {
                    "example": {
                        "product_id": 1,
                        "order_id": 1,
                        "user_name": "John Doe",
                        "user_email": "john@example.com",
                        "rating": 5,
                        "text": "Great product!",
                        "image_url": None,
                        "is_approved": False,
                        "is_published": False,
                        "report_count": 0,
                        "id": 1,
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00",
                    }
                }
            },
        },
        400: {
            "description": "Invalid data",
            "content": {"application/json": {"example": {"detail": "Invalid data", "support_id": "a1b2c3d4"}}},
        },
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Review not found",
            "content": {"application/json": {"example": {"detail": "Review not found", "support_id": "a1b2c3d4"}}},
        },
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_review(
    review_id: int,
    review_in: ReviewUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("reviews:update"))],
    review_service: ReviewServiceDep,
) -> dict[str, Any]:
    return await review_service.update(db, review_id, review_in)


@router.delete(
    "/{review_id}",
    status_code=204,
    responses={
        204: {"description": "Review deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Review not found",
            "content": {"application/json": {"example": {"detail": "Resource not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_review(
    review_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("reviews:delete"))],
    review_service: ReviewServiceDep,
) -> None:
    await review_service.delete(db, review_id)
