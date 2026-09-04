from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.auth.dependencies import get_current_user
from ...infrastructure.dependencies import AsyncSessionDep
from .dependencies import AddToCartServiceDep
from .schemas import AddToCartCheckout, AddToCartCreate, AddToCartItemCreate, AddToCartItemRead, AddToCartRead, AddToCartUpdate

router = APIRouter(tags=["Add to Cart"])

ADD_TO_CART_EXAMPLE = {
    "id": "0c2651e8-50f2-481c-87a6-b5199fef0b57",
    "customer_id": "019f5946-02d5-70b9-9b3a-e05205100c0c",
    "session_id": "abc12345",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "customer_phone": "08123456789",
    "subtotal": 1000000.0,
    "tax": 0.0,
    "discount": 0.0,
    "total": 1000000.0,
    "meta": {
        "source": "mobile_app"
    },
    "creator": None,
    "editor": None,
    "created_at": "2026-08-31T07:33:13.334021",
    "updated_at": "2026-08-31T07:33:13.334064",
    "customer": {
        "id": "019f5946-02d5-70b9-9b3a-e05205100c0c",
        "name": "Jane Doe Updated",
        "email": "jane.updated@example.com",
        "phone": "+6281234567899",
        "user_id": "608edd7a-afea-4714-9e66-c1fa3f58c424",
        "meta": None,
        "created_at": "2026-07-13T09:19:48",
        "updated_at": "2026-09-02T04:30:57",
        "addresses": [],
    },
    "items": [
        {
            "id": "cf9acc34-e80c-43f5-b18d-3621dc6858e8",
            "add_to_cart_id": "0c2651e8-50f2-481c-87a6-b5199fef0b57",
            "product_id": "d7e23a85-d835-430b-9c1b-0e29f8449697",
            "product_variant_id": "00034552-c2b9-49d6-8b5e-62a4dcb4f295",
            "variant_id": "00034552-c2b9-49d6-8b5e-62a4dcb4f295",
            "sku": "KBR001520011123S200160",
            "name": "KB GRAND X LB-17",
            "quantity": 1,
            "unit_price": 1000000.0,
            "total": 1000000.0,
            "discount_nominal": 0.0,
            "discount_percent": 0.0,
            "item_notes": "Tolong packing aman",
            "meta": {},
            "created_at": "2026-08-31T07:33:13.338526",
            "updated_at": "2026-08-31T07:33:13.338559",
            "product": {
                "id": "d7e23a85-d835-430b-9c1b-0e29f8449697",
                "name": "KB ROYAL EXCLUSIVE VIP RKB-09",
                "slug": "kb-royal-exclusive-vip-rkb-09",
                "category_id": None,
                "brand_id": None,
                "thumbnail": None,
                "alt_text": None,
                "short_description": None,
                "description": None,
                "best_seller": False,
                "is_new": False,
                "status": 1,
                "uom": None,
                "segments": None,
                "images": [],
                "variants": [],
                "colors": [],
                "price_product_settings": [],
                "reviews": [],
                "suggestions": [],
                "avg_rating": 0.0,
                "total_reviews": 0,
                "final_price": 0.0,
            },
            "variant": {
                "id": "00034552-c2b9-49d6-8b5e-62a4dcb4f295",
                "product_id": "d7e23a85-d835-430b-9c1b-0e29f8449697",
                "sku": "KBR001520011123S200160",
                "variant_name": "200 X 160",
                "width": 0.0,
                "length": 0.0,
                "height": 0.0,
                "weight": 0.0,
                "base_price": 0.0,
                "sell_price": 0.0,
                "stock_qty": 0,
                "attributes": None,
                "price_product_settings": [],
                "final_price": 0.0,
            },
        }
    ],
}


@router.get(
    "/",
    response_model=PaginatedListResponse[AddToCartRead],
    summary="List Add to Cart",
    description="Get a list of buffers.",
    responses={
        200: {
            "description": "A paginated list of buffers",
            "content": {
                "application/json": {
                    "example": {
                        "data": [ADD_TO_CART_EXAMPLE],
                        "total_count": 1,
                        "has_more": False,
                        "page": 1,
                        "items_per_page": 10,
                    }
                }
            },
        },
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def list_add_to_carts(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    add_to_cart_service: AddToCartServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await add_to_cart_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/{add_to_cart_id}",
    response_model=AddToCartRead,
    summary="Get AddToCart",
    description="Get a single add_to_cart by ID.",
    responses={
        200: {
            "description": "The requested add_to_cart",
            "content": {"application/json": {"example": ADD_TO_CART_EXAMPLE}},
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
            "description": "AddToCart not found",
            "content": {"application/json": {"example": {"detail": "AddToCart not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def get_add_to_cart(
    add_to_cart_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    add_to_cart_service: AddToCartServiceDep,
) -> dict[str, Any]:
    return await add_to_cart_service.get_by_id(db, add_to_cart_id)


@router.post(
    "/",
    response_model=AddToCartRead,
    status_code=201,
    summary="Create AddToCart",
    description="Create a new add_to_cart.",
    responses={
        201: {
            "description": "AddToCart created",
            "content": {"application/json": {"example": ADD_TO_CART_EXAMPLE}},
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
    },
)
async def create_add_to_cart(
    buffer_in: AddToCartCreate,
    db: AsyncSessionDep,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    add_to_cart_service: AddToCartServiceDep,
) -> dict[str, Any]:
    creator_id = UUID(str(current_user["id"])) if current_user and current_user.get("id") else None
    return await add_to_cart_service.create(db, buffer_in, creator_id=creator_id)


@router.put(
    "/{add_to_cart_id}",
    response_model=AddToCartRead,
    summary="Update AddToCart",
    description="Update an existing add_to_cart.",
    responses={
        200: {
            "description": "AddToCart updated",
            "content": {"application/json": {"example": ADD_TO_CART_EXAMPLE}},
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
            "description": "AddToCart not found",
            "content": {"application/json": {"example": {"detail": "AddToCart not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_add_to_cart(
    add_to_cart_id: UUID,
    buffer_in: AddToCartUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    add_to_cart_service: AddToCartServiceDep,
) -> dict[str, Any]:
    return await add_to_cart_service.update(db, add_to_cart_id, buffer_in)


@router.delete(
    "/{add_to_cart_id}",
    status_code=204,
    summary="Delete AddToCart",
    description="Remove a add_to_cart.",
    responses={
        204: {"description": "AddToCart deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "AddToCart not found",
            "content": {"application/json": {"example": {"detail": "AddToCart not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_add_to_cart(
    add_to_cart_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    add_to_cart_service: AddToCartServiceDep,
) -> None:
    await add_to_cart_service.delete(db, add_to_cart_id)


@router.post(
    "/{add_to_cart_id}/items",
    response_model=AddToCartItemRead,
    status_code=201,
    summary="Add AddToCart Item",
    description="Add an item to a add_to_cart.",
    responses={
        201: {
            "description": "AddToCart item created",
            "content": {"application/json": {"example": ADD_TO_CART_EXAMPLE["items"][0]}},
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
            "description": "AddToCart not found",
            "content": {"application/json": {"example": {"detail": "AddToCart not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def add_add_to_cart_item(
    add_to_cart_id: UUID,
    item_in: AddToCartItemCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    add_to_cart_service: AddToCartServiceDep,
) -> dict[str, Any]:
    return await add_to_cart_service.add_item(db, add_to_cart_id, item_in)


@router.put(
    "/{add_to_cart_id}/items/{item_id}",
    response_model=AddToCartItemRead,
    summary="Update AddToCart Item",
    description="Update an item in a add_to_cart.",
    responses={
        200: {
            "description": "AddToCart item updated",
            "content": {"application/json": {"example": ADD_TO_CART_EXAMPLE["items"][0]}},
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
            "description": "AddToCart or item not found",
            "content": {"application/json": {"example": {"detail": "AddToCart item not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_add_to_cart_item(
    add_to_cart_id: UUID,
    item_id: UUID,
    item_in: AddToCartItemCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    add_to_cart_service: AddToCartServiceDep,
) -> dict[str, Any]:
    return await add_to_cart_service.update_item(db, add_to_cart_id, item_id, item_in)


@router.delete(
    "/{add_to_cart_id}/items/{item_id}",
    status_code=204,
    summary="Delete AddToCart Item",
    description="Remove an item from a add_to_cart.",
    responses={
        204: {"description": "AddToCart item deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "AddToCart or item not found",
            "content": {"application/json": {"example": {"detail": "AddToCart item not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_add_to_cart_item(
    add_to_cart_id: UUID,
    item_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    add_to_cart_service: AddToCartServiceDep,
) -> None:
    await add_to_cart_service.delete_item(db, add_to_cart_id, item_id)


@router.post(
    "/{add_to_cart_id}/checkout",
    response_model=dict[str, Any],
    summary="Checkout AddToCart",
    description="Convert add_to_cart to an order and hard-delete the add_to_cart.",
    responses={
        200: {
            "description": "Order created from add_to_cart",
            "content": {"application/json": {"example": ADD_TO_CART_EXAMPLE}},
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
            "description": "AddToCart not found or empty",
            "content": {"application/json": {"example": {"detail": "AddToCart not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def checkout_add_to_cart(
    add_to_cart_id: UUID,
    checkout_in: AddToCartCheckout,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    add_to_cart_service: AddToCartServiceDep,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    creator_id = current_user.get("id") or current_user.get("sub")
    return await add_to_cart_service.checkout(db, add_to_cart_id, checkout_in, creator_id)
