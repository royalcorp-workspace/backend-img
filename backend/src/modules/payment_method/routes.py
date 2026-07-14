from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import PaymentMethodServiceDep
from .schemas import PaymentMethodCreate, PaymentMethodRead, PaymentMethodUpdate

router = APIRouter(tags=["Payment Methods"])

PAYMENT_METHOD_EXAMPLE = {
    "id": 1,
    "code": "BCA_VA",
    "name": "BCA Virtual Account",
    "type": "virtual_account",
    "provider": "Midtrans",
    "image": "https://example.com/bca.png",
    "has_charge": True,
    "charge_type": "fixed",
    "charge_value": 4000.0,
    "charge_bearer": "customer",
    "minimum_amount": 10000.0,
    "maximum_amount": None,
    "sort_order": 1,
    "status": True,
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
}


@router.get(
    "/",
    response_model=PaginatedListResponse[PaymentMethodRead],
    summary="List Payment Methods",
    description="Get a list of payment methods.",
    responses={
        200: {
            "description": "A paginated list of payment methods",
            "content": {
                "application/json": {
                    "example": {
                        "data": [PAYMENT_METHOD_EXAMPLE],
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
async def list_payment_methods(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("payment-methods:read"))],
    payment_method_service: PaymentMethodServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await payment_method_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/{method_id}",
    response_model=PaymentMethodRead,
    summary="Get Payment Method",
    description="Get a single payment method by ID.",
    responses={
        200: {
            "description": "The requested payment method",
            "content": {
                "application/json": {
                    "example": PAYMENT_METHOD_EXAMPLE
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
            "description": "Payment method not found",
            "content": {"application/json": {"example": {"detail": "Payment method not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def get_payment_method(
    method_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("payment-methods:read"))],
    payment_method_service: PaymentMethodServiceDep,
) -> dict[str, Any]:
    return await payment_method_service.get_by_id(db, method_id)


@router.post(
    "/",
    response_model=PaymentMethodRead,
    status_code=201,
    summary="Create Payment Method",
    description="Create a new payment method.",
    responses={
        201: {
            "description": "Payment method created",
            "content": {
                "application/json": {
                    "example": PAYMENT_METHOD_EXAMPLE
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
async def create_payment_method(
    method_in: PaymentMethodCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("payment-methods:create"))],
    payment_method_service: PaymentMethodServiceDep,
) -> dict[str, Any]:
    try:
        return await payment_method_service.create(db, method_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/{method_id}",
    response_model=PaymentMethodRead,
    summary="Update Payment Method",
    description="Update an existing payment method.",
    responses={
        200: {
            "description": "Payment method updated",
            "content": {
                "application/json": {
                    "example": PAYMENT_METHOD_EXAMPLE
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
            "description": "Payment method not found",
            "content": {"application/json": {"example": {"detail": "Payment method not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_payment_method(
    method_id: int,
    method_in: PaymentMethodUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("payment-methods:update"))],
    payment_method_service: PaymentMethodServiceDep,
) -> dict[str, Any]:
    try:
        return await payment_method_service.update(db, method_id, method_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/{method_id}",
    status_code=204,
    summary="Delete Payment Method",
    description="Remove a payment method.",
    responses={
        204: {"description": "Payment method deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Payment method not found",
            "content": {"application/json": {"example": {"detail": "Payment method not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_payment_method(
    method_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("payment-methods:delete"))],
    payment_method_service: PaymentMethodServiceDep,
) -> None:
    await payment_method_service.delete(db, method_id)
