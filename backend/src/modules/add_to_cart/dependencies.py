from typing import Annotated

from fastapi import Depends

from .service import AddToCartService


def get_add_to_cart_service() -> AddToCartService:
    return AddToCartService()


AddToCartServiceDep = Annotated[AddToCartService, Depends(get_add_to_cart_service)]
