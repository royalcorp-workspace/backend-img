from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.dependencies import AsyncSessionDep
from ...infrastructure.auth.dependencies import get_current_user
from ...modules.rbac.dependencies import require_permission
from .dependencies import BufferServiceDep
from .schemas import BufferCheckout, BufferCreate, BufferItemCreate, BufferItemRead, BufferRead, BufferUpdate

router = APIRouter(tags=["Buffers"])

BUFFER_EXAMPLE = {
    "id": "12345678-1234-1234-1234-123456789012",
    "customer_id": "12345678-1234-1234-1234-123456789013",
    "session_id": "abc123",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "customer_phone": "081234567890",
    "subtotal": 1000000.0,
    "tax": 0.0,
    "discount": 0.0,
    "total": 1000000.0,
    "meta": None,
    "creator": "12345678-1234-1234-1234-123456789014",
    "editor": "12345678-1234-1234-1234-123456789014",
    "created_at": "2026-07-21T08:00:00",
    "updated_at": "2026-07-21T08:00:00",
    "customer": {
        "id": "12345678-1234-1234-1234-123456789013",
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "081234567890",
        "user_id": None,
        "meta": None,
        "created_at": "2026-07-21T08:00:00",
        "updated_at": "2026-07-21T08:00:00",
    },
    "items": [
        {
            "id": "12345678-1234-1234-1234-123456789015",
            "buffer_id": "12345678-1234-1234-1234-123456789012",
            "product_id": "12345678-1234-1234-1234-123456789016",
            "product_variant_id": None,
            "name": "Product Name",
            "quantity": 1,
            "unit_price": 1000000.0,
            "total": 1000000.0,
            "discount_nominal": 0.0,
            "discount_percent": 0.0,
            "item_notes": None,
            "meta": None,
            "created_at": "2026-07-21T08:00:00",
            "updated_at": "2026-07-21T08:00:00",
            "product": {
                "id": "12345678-1234-1234-1234-123456789016",
                "name": "Product Name",
                "slug": "product-name",
                "base_price": "1000000",
            },
            "variant": None,
        }
    ],
}


@router.get(
    "/",
    response_model=PaginatedListResponse[BufferRead],
    summary="List Buffers",
    description="Get a list of buffers.",
    responses={
        200: {
            "description": "A paginated list of buffers",
            "content": {
                "application/json": {
                    "example": {
                        "data": [BUFFER_EXAMPLE],
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
async def list_buffers(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("buffers:read"))],
    buffer_service: BufferServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await buffer_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/{buffer_id}",
    response_model=BufferRead,
    summary="Get Buffer",
    description="Get a single buffer by ID.",
    responses={
        200: {
            "description": "The requested buffer",
            "content": {"application/json": {"example": BUFFER_EXAMPLE}},
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
            "description": "Buffer not found",
            "content": {"application/json": {"example": {"detail": "Buffer not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def get_buffer(
    buffer_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("buffers:read"))],
    buffer_service: BufferServiceDep,
) -> dict[str, Any]:
    return await buffer_service.get_by_id(db, buffer_id)


@router.post(
    "/",
    response_model=BufferRead,
    status_code=201,
    summary="Create Buffer",
    description="Create a new buffer.",
    responses={
        201: {
            "description": "Buffer created",
            "content": {"application/json": {"example": BUFFER_EXAMPLE}},
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
async def create_buffer(
    buffer_in: BufferCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("buffers:create"))],
    buffer_service: BufferServiceDep,
) -> dict[str, Any]:
    return await buffer_service.create(db, buffer_in)


@router.put(
    "/{buffer_id}",
    response_model=BufferRead,
    summary="Update Buffer",
    description="Update an existing buffer.",
    responses={
        200: {
            "description": "Buffer updated",
            "content": {"application/json": {"example": BUFFER_EXAMPLE}},
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
            "description": "Buffer not found",
            "content": {"application/json": {"example": {"detail": "Buffer not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_buffer(
    buffer_id: UUID,
    buffer_in: BufferUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("buffers:update"))],
    buffer_service: BufferServiceDep,
) -> dict[str, Any]:
    return await buffer_service.update(db, buffer_id, buffer_in)


@router.delete(
    "/{buffer_id}",
    status_code=204,
    summary="Delete Buffer",
    description="Remove a buffer.",
    responses={
        204: {"description": "Buffer deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Buffer not found",
            "content": {"application/json": {"example": {"detail": "Buffer not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_buffer(
    buffer_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("buffers:delete"))],
    buffer_service: BufferServiceDep,
) -> None:
    await buffer_service.delete(db, buffer_id)


@router.post(
    "/{buffer_id}/items",
    response_model=BufferItemRead,
    status_code=201,
    summary="Add Buffer Item",
    description="Add an item to a buffer.",
    responses={
        201: {
            "description": "Buffer item created",
            "content": {"application/json": {"example": BUFFER_EXAMPLE["items"][0]}},
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
            "description": "Buffer not found",
            "content": {"application/json": {"example": {"detail": "Buffer not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def add_buffer_item(
    buffer_id: UUID,
    item_in: BufferItemCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("buffers:update"))],
    buffer_service: BufferServiceDep,
) -> dict[str, Any]:
    return await buffer_service.add_item(db, buffer_id, item_in)


@router.put(
    "/{buffer_id}/items/{item_id}",
    response_model=BufferItemRead,
    summary="Update Buffer Item",
    description="Update an item in a buffer.",
    responses={
        200: {
            "description": "Buffer item updated",
            "content": {"application/json": {"example": BUFFER_EXAMPLE["items"][0]}},
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
            "description": "Buffer or item not found",
            "content": {"application/json": {"example": {"detail": "Buffer item not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_buffer_item(
    buffer_id: UUID,
    item_id: UUID,
    item_in: BufferItemCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("buffers:update"))],
    buffer_service: BufferServiceDep,
) -> dict[str, Any]:
    return await buffer_service.update_item(db, buffer_id, item_id, item_in)


@router.delete(
    "/{buffer_id}/items/{item_id}",
    status_code=204,
    summary="Delete Buffer Item",
    description="Remove an item from a buffer.",
    responses={
        204: {"description": "Buffer item deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Buffer or item not found",
            "content": {"application/json": {"example": {"detail": "Buffer item not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_buffer_item(
    buffer_id: UUID,
    item_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("buffers:update"))],
    buffer_service: BufferServiceDep,
) -> None:
    await buffer_service.delete_item(db, buffer_id, item_id)


@router.post(
    "/{buffer_id}/checkout",
    response_model=dict[str, Any],
    summary="Checkout Buffer",
    description="Convert buffer to an order and hard-delete the buffer.",
    responses={
        200: {
            "description": "Order created from buffer",
            "content": {"application/json": {"example": BUFFER_EXAMPLE}},
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
            "description": "Buffer not found or empty",
            "content": {"application/json": {"example": {"detail": "Buffer not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def checkout_buffer(
    buffer_id: UUID,
    checkout_in: BufferCheckout,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("buffers:create"))],
    buffer_service: BufferServiceDep,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    creator_id = current_user.get("id") or current_user.get("sub")
    return await buffer_service.checkout(db, buffer_id, checkout_in, creator_id)
