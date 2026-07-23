from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import CourierServiceDep
from .schemas import (
    CourierCreate,
    CourierRead,
    CourierUpdate,
    ShippingAddressCreate,
    ShippingAddressRead,
    ShippingAddressUpdate,
)

router = APIRouter()

COURIER_EXAMPLE = {
    "id": "ac2fda49-d3cd-4e0b-8c74-3be6ae4133f0",
    "code": "jne",
    "name": "JNE Express",
    "type": 1,
    "is_active": True,
    "sort_order": 1,
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
    "shipping_addresses": [],
}

SHIPPING_ADDRESS_EXAMPLE = {
    "id": "019f5a2e-c083-72ac-9a70-c80c9eb5532f",
    "courier_id": "ac2fda49-d3cd-4e0b-8c74-3be6ae4133f0",
    "sub_district_id": "2202ecf7-e399-4565-9a8f-37b91d683912",
    "type": 2,
    "price": 1000.0,
    "is_active": True,
    "sort_order": 0,
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
    "courier": {
        "id": "ac2fda49-d3cd-4e0b-8c74-3be6ae4133f0",
        "code": "jne",
        "name": "JNE Express",
        "type": 1,
        "is_active": True,
        "sort_order": 1,
    },
}


# ==========================================
# 1. COURIERS
# ==========================================
@router.get(
    "/",
    response_model=PaginatedListResponse[CourierRead],
    summary="List Couriers",
    description="Get a list of couriers.",
    tags=["Couriers"],
    responses={
        200: {
            "description": "A paginated list of couriers",
            "content": {
                "application/json": {
                    "example": {
                        "data": [COURIER_EXAMPLE],
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
async def list_couriers(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:read"))],
    courier_service: CourierServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await courier_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/{courier_id}",
    response_model=CourierRead,
    summary="Get Courier",
    description="Get a single courier by ID.",
    tags=["Couriers"],
    responses={
        200: {
            "description": "The requested courier",
            "content": {
                "application/json": {
                    "example": COURIER_EXAMPLE
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
            "description": "Courier not found",
            "content": {"application/json": {"example": {"detail": "Courier not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def get_courier(
    courier_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:read"))],
    courier_service: CourierServiceDep,
) -> dict[str, Any]:
    return await courier_service.get_by_id(db, courier_id)


@router.post(
    "/",
    response_model=CourierRead,
    status_code=201,
    summary="Create Courier",
    description="Create a new courier.",
    tags=["Couriers"],
    responses={
        201: {
            "description": "Courier created",
            "content": {
                "application/json": {
                    "example": COURIER_EXAMPLE
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
async def create_courier(
    courier_in: CourierCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:create"))],
    courier_service: CourierServiceDep,
) -> dict[str, Any]:
    try:
        return await courier_service.create(db, courier_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/{courier_id}",
    response_model=CourierRead,
    summary="Update Courier",
    description="Update an existing courier.",
    tags=["Couriers"],
    responses={
        200: {
            "description": "Courier updated",
            "content": {
                "application/json": {
                    "example": COURIER_EXAMPLE
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
            "description": "Courier not found",
            "content": {"application/json": {"example": {"detail": "Courier not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_courier(
    courier_id: UUID,
    courier_in: CourierUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:update"))],
    courier_service: CourierServiceDep,
) -> dict[str, Any]:
    try:
        return await courier_service.update(db, courier_id, courier_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/{courier_id}",
    status_code=204,
    summary="Delete Courier",
    description="Remove a courier.",
    tags=["Couriers"],
    responses={
        204: {"description": "Courier deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Courier not found",
            "content": {"application/json": {"example": {"detail": "Courier not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_courier(
    courier_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:delete"))],
    courier_service: CourierServiceDep,
) -> None:
    await courier_service.delete(db, courier_id)


# ==========================================
# 2. SHIPPING ADDRESSES (RATES)
# ==========================================
@router.get(
    "/shipping-addresses/",
    response_model=PaginatedListResponse[ShippingAddressRead],
    summary="List Shipping Addresses (Rates)",
    description="Get a list of shipping rates / addresses.",
    tags=["Shipping Addresses"],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "data": [SHIPPING_ADDRESS_EXAMPLE],
                        "total_count": 1,
                        "has_more": False,
                        "page": 1,
                        "items_per_page": 10,
                    }
                }
            }
        }
    },
)
async def list_shipping_addresses(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:read"))],
    courier_service: CourierServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await courier_service.get_shipping_addresses_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/shipping-addresses/{address_id}",
    response_model=ShippingAddressRead,
    summary="Get Shipping Address Rate",
    tags=["Shipping Addresses"],
    responses={200: {"content": {"application/json": {"example": SHIPPING_ADDRESS_EXAMPLE}}}},
)
async def get_shipping_address(
    address_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:read"))],
    courier_service: CourierServiceDep,
) -> dict[str, Any]:
    return await courier_service.get_shipping_address_by_id(db, address_id)


@router.post(
    "/shipping-addresses/",
    response_model=ShippingAddressRead,
    status_code=201,
    summary="Create Shipping Address Rate",
    tags=["Shipping Addresses"],
    responses={201: {"content": {"application/json": {"example": SHIPPING_ADDRESS_EXAMPLE}}}},
)
async def create_shipping_address(
    address_in: ShippingAddressCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:create"))],
    courier_service: CourierServiceDep,
) -> dict[str, Any]:
    try:
        return await courier_service.create_shipping_address(db, address_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/shipping-addresses/{address_id}",
    response_model=ShippingAddressRead,
    summary="Update Shipping Address Rate",
    tags=["Shipping Addresses"],
    responses={200: {"content": {"application/json": {"example": SHIPPING_ADDRESS_EXAMPLE}}}},
)
async def update_shipping_address(
    address_id: UUID,
    address_in: ShippingAddressUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:update"))],
    courier_service: CourierServiceDep,
) -> dict[str, Any]:
    try:
        return await courier_service.update_shipping_address(db, address_id, address_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/shipping-addresses/{address_id}",
    status_code=204,
    summary="Delete Shipping Address Rate",
    tags=["Shipping Addresses"],
)
async def delete_shipping_address(
    address_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("couriers:delete"))],
    courier_service: CourierServiceDep,
) -> None:
    await courier_service.delete_shipping_address(db, address_id)
