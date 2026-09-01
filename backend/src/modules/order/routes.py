from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.dependencies import AsyncSessionDep
from ...infrastructure.auth.dependencies import get_current_user
from .dependencies import OrderServiceDep
from .schemas import OrderCreate, OrderRead


ORDER_CREATE_DIRECT_EXAMPLE = {
    "customer_id": "123e4567-e89b-12d3-a456-426614174000",
    "shipping_address_id": "223e4567-e89b-12d3-a456-426614174001",
    "courier_id": "jne",
    "payment_method": "bank_transfer",
    "subtotal": 1250000.0,
    "shipping_cost": 25000.0,
    "total": 1275000.0,
    "items": [
        {
            "product_id": "25043f8a-7517-4caa-a8bb-144e8e6e7a78",
            "product_variant_id": "88043f8a-7517-4caa-a8bb-144e8e6e7a88",
            "quantity": 1,
            "unit_price": 1250000.0,
            "total": 1250000.0,
            "name": "KB GRAND X LB-17",
            "item_notes": "Beli Langsung"
        }
    ]
}

ORDER_CREATE_CART_EXAMPLE = {
    "customer_id": "123e4567-e89b-12d3-a456-426614174000",
    "shipping_address_id": "223e4567-e89b-12d3-a456-426614174001",
    "courier_id": "jne",
    "payment_method": "credit_card",
    "subtotal": 2500000.0,
    "shipping_cost": 50000.0,
    "total": 2550000.0,
    "cart_item_ids": [
        "323e4567-e89b-12d3-a456-426614174002",
        "423e4567-e89b-12d3-a456-426614174003"
    ]
}


router = APIRouter(tags=["Orders"])

# Realistic example order response
ORDER_EXAMPLE = {
    "id": "8f30c3a2-b911-4a4b-841a-e4b51a5c6d70",
    "customer_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": 2,
    "payment_method": "BCAATM",
    "payment_status": 2,
    "subtotal": 1250000.0,
    "tax": 0.0,
    "discount": 0.0,
    "total": 1250000.0,
    "notes": "Tolong packing kayu",
    "meta": {"platform": "mobile_app"},
    "creator": "system",
    "editor": "system",
    "created_at": "2026-08-28T14:30:00",
    "updated_at": "2026-08-28T14:35:00",
    "customer": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Budi Santoso",
        "email": "budi@example.com",
        "phone": "08123456789",
        "user_id": "u1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5",
        "created_at": "2026-08-01T10:00:00",
        "updated_at": "2026-08-01T10:00:00"
    },
    "items": [
        {
            "id": "i1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5",
            "order_id": "8f30c3a2-b911-4a4b-841a-e4b51a5c6d70",
            "product_id": "25043f8a-7517-4caa-a8bb-144e8e6e7a78",
            "product_variant_id": "88043f8a-7517-4caa-a8bb-144e8e6e7a88",
            "quantity": 1,
            "unit_price": 1250000.0,
            "discount_nominal": 0.0,
            "discount_percent": 0.0,
            "total": 1250000.0,
            "name": "KB GRAND X LB-17",
            "item_notes": "Merah",
            "meta": {},
            "created_at": "2026-08-28T14:30:00",
            "updated_at": "2026-08-28T14:30:00",
            "product": {
                "id": "25043f8a-7517-4caa-a8bb-144e8e6e7a78",
                "name": "KB GRAND X LB-17",
                "slug": "kb-grand-x-lb-17",
                "base_price": 1250000.0
            },
            "variant": {
                "id": "88043f8a-7517-4caa-a8bb-144e8e6e7a88",
                "product_id": "25043f8a-7517-4caa-a8bb-144e8e6e7a78",
                "variant_name": "120 x 200",
                "price": 1250000.0,
                "sku": "KBGRAND120200"
            }
        }
    ]
}



@router.get(
    "/",
    response_model=PaginatedListResponse[OrderRead],
    summary="List Orders",
    description="Get a list of orders.",
    responses={
        200: {
            "description": "A paginated list of orders",
            "content": {
                "application/json": {
                    "example": {
                        "data": [ORDER_EXAMPLE],
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
async def list_orders(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    order_service: OrderServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await order_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    summary="Get Order",
    description="Get a single order by ID.",
    responses={
        200: {
            "description": "The requested order",
            "content": {
                "application/json": {
                    "example": ORDER_EXAMPLE
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
        404: {
            "description": "Order not found",
            "content": {"application/json": {"example": {"detail": "Order not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def get_order(
    order_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    order_service: OrderServiceDep,
) -> dict[str, Any]:
    return await order_service.get_by_id(db, order_id)


@router.post(
    "/",
    response_model=OrderRead,
    status_code=201,
    summary="Create Order",
    description="Create a new order with items.",
    responses={
        201: {
            "description": "Order created",
            "content": {
                "application/json": {
                    "examples": {
                        "Direct Purchase": {
                            "summary": "Beli Langsung",
                            "value": ORDER_CREATE_DIRECT_EXAMPLE
                        },
                        "From Cart": {
                            "summary": "Dari Keranjang",
                            "value": ORDER_CREATE_CART_EXAMPLE
                        }
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
    },
)
async def create_order(
    order_in: OrderCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    order_service: OrderServiceDep,
) -> dict[str, Any]:
    return await order_service.create(db, order_in)




@router.delete(
    "/{order_id}",
    status_code=204,
    summary="Delete Order",
    description="Remove an order.",
    responses={
        204: {"description": "Order deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Order not found",
            "content": {"application/json": {"example": {"detail": "Order not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_order(
    order_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    order_service: OrderServiceDep,
) -> None:
    await order_service.delete(db, order_id)
