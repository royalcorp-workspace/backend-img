from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from .dependencies import OrderServiceDep
from .schemas import OrderCreate, OrderRead, OrderUpdate

router = APIRouter(tags=["Orders"])

# Realistic example order response
ORDER_EXAMPLE = {
    "id": 1,
    "customer_id": 1,
    "status": 0,
    "payment_method": "credit_card",
    "payment_status": "paid",
    "subtotal": 1000000.0,
    "tax": 100000.0,
    "discount": 0.0,
    "total": 1100000.0,
    "notes": "Handle with care",
    "meta": None,
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
    "customer": {
        "id": 1,
        "name": "Budi Santoso",
        "email": "budi.santoso@example.com",
        "phone": "081234567890",
        "user_id": 2,
        "meta": None,
        "created_at": "2026-07-09T13:00:00",
        "updated_at": "2026-07-09T13:00:00"
    },
    "items": [
        {
            "id": 1,
            "order_id": 1,
            "product_id": 1,
            "product_variant_id": 1,
            "product_color_id": None,
            "quantity": 1,
            "unit_price": 1000000.0,
            "discount_nominal": 0.0,
            "discount_percent": 0.0,
            "total": 1000000.0,
            "weight": 0,
            "name": "Product Name",
            "item_notes": None,
            "meta": None,
            "created_at": "2026-07-09T13:00:00",
            "updated_at": "2026-07-09T13:00:00",
            "product": {
                "id": 1,
                "name": "DV (L1) HOTEL CLASSIC LH-8",
                "slug": "dvl100220010607",
                "category_id": 3,
                "thumbnail": "https://example.com/images/dvl100220010607.jpg",
                "alt_text": "DV (L1) HOTEL CLASSIC LH-8 Image",
                "short_description": "200 X 090",
                "description": "Produk disinkronkan dari POS JDE: DV (L1) HOTEL CLASSIC LH-8",
                "base_price": 0.0,
                "segments": {
                    "uom": "PC",
                    "segment1": "DV",
                    "segment2": "L1002200",
                    "segment3": "10607",
                    "segment4": "S",
                    "segment5": "200",
                    "segment6": "090"
                },
                "best_seller": True,
                "is_new": False,
                "sort_order": 1,
                "status": 1,
                "created_at": "2026-07-09T13:00:00",
                "updated_at": "2026-07-09T13:00:00"
            },
            "variant": {
                "id": 1,
                "product_id": 1,
                "sku": "DVL100220010607S200090",
                "variant_name": "200 X 090",
                "price": 0.0,
                "stock_qty": 0,
                "attributes": {},
                "created_at": "2026-07-09T13:00:00",
                "updated_at": "2026-07-09T13:00:00"
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
    _: Annotated[dict[str, Any], Depends(require_permission("orders:read"))],
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
    _: Annotated[dict[str, Any], Depends(require_permission("orders:read"))],
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
                    "example": ORDER_EXAMPLE
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
    _: Annotated[dict[str, Any], Depends(require_permission("orders:create"))],
    order_service: OrderServiceDep,
) -> dict[str, Any]:
    return await order_service.create(db, order_in)


@router.put(
    "/{order_id}",
    response_model=OrderRead,
    summary="Update Order",
    description="Update an existing order.",
    responses={
        200: {
            "description": "Order updated",
            "content": {
                "application/json": {
                    "example": ORDER_EXAMPLE
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
            "description": "Order not found",
            "content": {"application/json": {"example": {"detail": "Order not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_order(
    order_id: UUID,
    order_in: OrderUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("orders:update"))],
    order_service: OrderServiceDep,
) -> dict[str, Any]:
    return await order_service.update(db, order_id, order_in)


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
    _: Annotated[dict[str, Any], Depends(require_permission("orders:delete"))],
    order_service: OrderServiceDep,
) -> None:
    await order_service.delete(db, order_id)
