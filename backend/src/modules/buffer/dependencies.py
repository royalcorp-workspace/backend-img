from typing import Annotated

from fastapi import Depends

from .service import BufferService


def get_buffer_service() -> BufferService:
    return BufferService()


BufferServiceDep = Annotated[BufferService, Depends(get_buffer_service)]
