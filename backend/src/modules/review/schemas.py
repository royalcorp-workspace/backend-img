from typing import Annotated

from pydantic import BaseModel, Field

from ..common.schemas import TimestampSchema


class ReviewBase(BaseModel):
    product_id: int
    order_id: int | None = None
    user_name: str | None = None
    user_email: str | None = None
    rating: Annotated[int, Field(ge=1, le=5)]
    text: str | None = None
    image_url: str | None = None
    is_approved: bool = False
    is_published: bool = False
    report_count: int | None = 0


class Review(ReviewBase, TimestampSchema):
    id: int


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: int | None = None
    text: str | None = None
    image_url: str | None = None
    is_approved: bool | None = None
    is_published: bool | None = None
    report_count: int | None = None


class ReviewRead(ReviewBase):
    id: int


class ProductReviewsRead(BaseModel):
    reviews: list[ReviewRead]
    avg_rating: float
    total_reviews: int
