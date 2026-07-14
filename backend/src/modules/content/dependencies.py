from typing import Annotated

from fastapi import Depends

from .service import ContentService, content_service


async def get_content_service() -> ContentService:
    return content_service


ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
