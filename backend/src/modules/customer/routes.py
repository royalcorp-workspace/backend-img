from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import CustomerServiceDep
from .schemas import AddressCreate, CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(tags=["Customers"])

CUSTOMER_EXAMPLE = {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "phone": "+6281234567890",
    "meta": None,
    "addresses": [
        {
            "id": "223e4567-e89b-12d3-a456-426614174001",
            "customer_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "label": "Rumah",
            "recipient_name": "Jane Doe",
            "phone": "+6281234567890",
            "address": "Jl. Hayam Wuruk No. 12, Gambir",
            "city_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "city_name": "Kota Administrasi Jakarta Pusat",
            "sub_district_id": "4fa85f64-5717-4562-b3fc-2c963f66afa6",
            "sub_district_name": "Gambir",
            "district_name": "Gambir",
            "province_id": "31",
            "province_name": "DKI Jakarta",
            "postal_code": "10120",
            "is_primary": True,
            "created_at": "2026-07-09T13:00:00",
            "updated_at": "2026-07-09T13:00:00",
        }
    ],
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
}


@router.get(
    "/",
    response_model=PaginatedListResponse[CustomerRead],
    summary="List Customers",
    description="Get a paginated list of customers with full address and region details.",
    responses={
        200: {
            "description": "A paginated list of customers",
            "content": {
                "application/json": {
                    "example": {
                        "data": [CUSTOMER_EXAMPLE],
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
async def list_customers(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("customers:read"))],
    customer_service: CustomerServiceDep,
    page: int = 1,
    items_per_page: int = 10,
    search: str | None = None,
) -> dict[str, Any]:
    filters = {}
    if search:
        filters["name__ilike"] = f"%{search}%"
    data = await customer_service.get_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page, **filters
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.post(
    "/",
    response_model=CustomerRead,
    status_code=201,
    summary="Create Customer",
    description="Create a new customer and optionally add their initial addresses.",
    responses={
        201: {
            "description": "The created customer",
            "content": {"application/json": {"example": CUSTOMER_EXAMPLE}},
        },
        400: {
            "description": "Invalid request",
            "content": {"application/json": {"example": {"detail": "Invalid request", "support_id": "a1b2c3d4"}}},
        },
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        409: {
            "description": "Customer already exists",
            "content": {"application/json": {"example": {"detail": "Customer already exists", "support_id": "a1b2c3d4"}}},
        },
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("customers:create"))],
    customer_service: CustomerServiceDep,
) -> dict[str, Any]:
    try:
        return await customer_service.create(db, customer_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get(
    "/{customer_id}",
    response_model=CustomerRead,
    summary="Get Customer",
    description="Get a single customer by ID with full address details up to province.",
    responses={
        200: {
            "description": "The requested customer",
            "content": {"application/json": {"example": CUSTOMER_EXAMPLE}},
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
            "description": "Customer not found",
            "content": {"application/json": {"example": {"detail": "Customer not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def get_customer(
    customer_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("customers:read"))],
    customer_service: CustomerServiceDep,
) -> dict[str, Any]:
    return await customer_service.get_by_id(db, customer_id)


@router.put(
    "/{customer_id}",
    response_model=CustomerRead,
    summary="Update Customer",
    description="Update an existing customer and optionally update/create addresses. If an address object contains 'id', 'address_id', or 'addresses_id', it updates that existing address.",
    responses={
        200: {
            "description": "The updated customer",
            "content": {"application/json": {"example": CUSTOMER_EXAMPLE}},
        },
        400: {
            "description": "Invalid request",
            "content": {"application/json": {"example": {"detail": "Invalid request", "support_id": "a1b2c3d4"}}},
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
            "description": "Customer not found",
            "content": {"application/json": {"example": {"detail": "Customer not found", "support_id": "a1b2c3d4"}}},
        },
        409: {
            "description": "Customer already exists",
            "content": {"application/json": {"example": {"detail": "Customer already exists", "support_id": "a1b2c3d4"}}},
        },
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_customer(
    customer_id: UUID,
    customer_in: CustomerUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("customers:update"))],
    customer_service: CustomerServiceDep,
) -> dict[str, Any]:
    try:
        return await customer_service.update(db, customer_id, customer_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post(
    "/{customer_id}/addresses",
    response_model=CustomerRead,
    status_code=201,
    summary="Add Customer Address",
    description="Add a new address specifically for an existing customer with full city, subdistrict, and province details.",
    responses={
        201: {
            "description": "Address added successfully, returns customer details with updated addresses",
            "content": {"application/json": {"example": CUSTOMER_EXAMPLE}},
        },
        400: {
            "description": "Invalid request",
            "content": {"application/json": {"example": {"detail": "Invalid request", "support_id": "a1b2c3d4"}}},
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
            "description": "Customer not found",
            "content": {"application/json": {"example": {"detail": "Customer not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def add_customer_address(
    customer_id: UUID,
    address_in: AddressCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("customers:create"))],
    customer_service: CustomerServiceDep,
) -> dict[str, Any]:
    try:
        return await customer_service.add_address(db, customer_id, address_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.patch(
    "/{customer_id}/addresses/{address_id}/primary",
    response_model=CustomerRead,
    summary="Set Primary Address",
    description="Set a specific address as primary for a customer. Other addresses will be set to non-primary.",
    responses={
        200: {"description": "Customer with updated primary address", "content": {"application/json": {"example": CUSTOMER_EXAMPLE}}},
        404: {"description": "Customer or address not found", "content": {"application/json": {"example": {"detail": "Customer or address not found", "support_id": "a1b2c3d4"}}}},
    },
)
async def set_primary_address(
    customer_id: UUID,
    address_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("customers:update"))],
    customer_service: CustomerServiceDep,
) -> dict[str, Any]:
    return await customer_service.set_primary_address(db, customer_id, address_id)

