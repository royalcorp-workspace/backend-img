from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..product.schemas import ProductCreate
from .dependencies import InventoryServiceDep
from .schemas import InventoryCreateResponse, InventoryRead

router = APIRouter(tags=["Inventory"])


@router.get(
    "/",
    response_model=PaginatedListResponse[InventoryRead],
    summary="List Inventory",
    description="Get a paginated list of inventory items.",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "data": [{"id": 1, "name": "Sample Item", "stock_qty": 100}],
                        "total_count": 1,
                        "has_more": False,
                        "page": 1,
                        "items_per_page": 10,
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Forbidden",
            "content": {"application/json": {"example": {"detail": "Forbidden", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def list_inventory(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("inventory:read"))],
    inventory_service: InventoryServiceDep,
    page: int = 1,
    items_per_page: int = 10,
    search: str | None = None,
) -> dict[str, Any]:
    filters = {}
    if search:
        filters["name__ilike"] = f"%{search}%"
    data = await inventory_service.get_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page, **filters
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.post(
    "/",
    response_model=InventoryCreateResponse,
    status_code=201,
    summary="Create Inventory Item",
    description="Create a new inventory item (product).",
    responses={
        201: {
            "description": "Created",
            "content": {"application/json": {"example": {"id": 1, "name": "New Item"}}},
        },
        400: {
            "description": "Bad Request",
            "content": {"application/json": {"example": {"detail": "Bad request", "support_id": "a1b2c3d4"}}},
        },
        401: {
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Forbidden",
            "content": {"application/json": {"example": {"detail": "Forbidden", "support_id": "a1b2c3d4"}}},
        },
        409: {
            "description": "Conflict",
            "content": {"application/json": {"example": {"detail": "Conflict", "support_id": "a1b2c3d4"}}},
        },
        422: {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid request. Please check your input and try again.", "support_id": "a1b2c3d4"}
                }
            },
        },
    },
)
async def create_inventory(
    product_in: dict,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("inventory:create"))],
    inventory_service: InventoryServiceDep,
) -> dict[str, Any]:
    product = ProductCreate(**product_in)
    return await inventory_service.create(db, product)
