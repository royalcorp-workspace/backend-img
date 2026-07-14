from typing import Annotated

from fastapi import Depends

from .service import ReviewService


def get_review_service() -> ReviewService:
    return ReviewService()


ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]
