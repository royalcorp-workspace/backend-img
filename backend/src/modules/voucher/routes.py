from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import VoucherServiceDep
from .schemas import VoucherCreate, VoucherRead, VoucherUpdate

router = APIRouter(tags=["Vouchers"])


@router.get(
    "/",
    response_model=PaginatedListResponse[VoucherRead],
    summary="List Vouchers",
    description="Get a paginated list of vouchers.",
    responses={
        200: {
            "description": "A paginated list of vouchers.",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": 1,
                                "code": "SAVE10",
                                "title": "10% Off",
                                "description": "10 percent discount on your order",
                                "type": "percentage",
                                "scope": "global",
                                "allow_stacking": False,
                                "value": 10.0,
                                "min_purchase": 0.0,
                                "max_discount": None,
                                "usage_limit": None,
                                "usage_limit_per_user": None,
                                "used_count": 0,
                                "start_date": "2026-01-01T00:00:00",
                                "end_date": "2026-12-31T23:59:59",
                                "valid_for_new_customer": False,
                                "is_active": True,
                                "created_at": "2026-01-01T00:00:00",
                                "updated_at": None,
                            }
                        ],
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
async def list_vouchers(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("vouchers:read"))],
    voucher_service: VoucherServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await voucher_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.post(
    "/",
    response_model=VoucherRead,
    status_code=201,
    summary="Create Voucher",
    description="Create a new voucher.",
    responses={
        201: {
            "description": "The created voucher.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "code": "SAVE10",
                        "title": "10% Off",
                        "description": "10 percent discount on your order",
                        "type": "percentage",
                        "scope": "global",
                        "allow_stacking": False,
                        "value": 10.0,
                        "min_purchase": 0.0,
                        "max_discount": None,
                        "usage_limit": None,
                        "usage_limit_per_user": None,
                        "used_count": 0,
                        "start_date": "2026-01-01T00:00:00",
                        "end_date": "2026-12-31T23:59:59",
                        "valid_for_new_customer": False,
                        "is_active": True,
                        "created_at": "2026-01-01T00:00:00",
                        "updated_at": None,
                    }
                }
            },
        },
        400: {
            "description": "Bad request",
            "content": {"application/json": {"example": {"detail": "Invalid voucher data provided", "support_id": "a1b2c3d4"}}},
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
            "description": "Conflict with an existing voucher",
            "content": {
                "application/json": {"example": {"detail": "A voucher with this code already exists", "support_id": "a1b2c3d4"}}
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid request. Please check your input and try again.", "support_id": "a1b2c3d4"}
                }
            },
        },
    },
)
async def create_voucher(
    voucher_in: VoucherCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("vouchers:create"))],
    voucher_service: VoucherServiceDep,
) -> dict[str, Any]:
    try:
        return await voucher_service.create(voucher_in, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get(
    "/{voucher_id}",
    response_model=VoucherRead,
    summary="Get Voucher",
    description="Get a single voucher by ID.",
    responses={
        200: {
            "description": "The requested voucher.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "code": "SAVE10",
                        "title": "10% Off",
                        "description": "10 percent discount on your order",
                        "type": "percentage",
                        "scope": "global",
                        "allow_stacking": False,
                        "value": 10.0,
                        "min_purchase": 0.0,
                        "max_discount": None,
                        "usage_limit": None,
                        "usage_limit_per_user": None,
                        "used_count": 0,
                        "start_date": "2026-01-01T00:00:00",
                        "end_date": "2026-12-31T23:59:59",
                        "valid_for_new_customer": False,
                        "is_active": True,
                        "created_at": "2026-01-01T00:00:00",
                        "updated_at": None,
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
        404: {
            "description": "Voucher not found",
            "content": {"application/json": {"example": {"detail": "Voucher not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def get_voucher(
    voucher_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("vouchers:read"))],
    voucher_service: VoucherServiceDep,
) -> dict[str, Any]:
    return await voucher_service.get_by_id(db, voucher_id)


@router.put(
    "/{voucher_id}",
    response_model=VoucherRead,
    summary="Update Voucher",
    description="Update an existing voucher.",
    responses={
        200: {
            "description": "The updated voucher.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "code": "SAVE10",
                        "title": "10% Off",
                        "description": "10 percent discount on your order",
                        "type": "percentage",
                        "scope": "global",
                        "allow_stacking": False,
                        "value": 10.0,
                        "min_purchase": 0.0,
                        "max_discount": None,
                        "usage_limit": None,
                        "usage_limit_per_user": None,
                        "used_count": 0,
                        "start_date": "2026-01-01T00:00:00",
                        "end_date": "2026-12-31T23:59:59",
                        "valid_for_new_customer": False,
                        "is_active": True,
                        "created_at": "2026-01-01T00:00:00",
                        "updated_at": None,
                    }
                }
            },
        },
        400: {
            "description": "Bad request",
            "content": {"application/json": {"example": {"detail": "Invalid voucher data provided", "support_id": "a1b2c3d4"}}},
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
            "description": "Voucher not found",
            "content": {"application/json": {"example": {"detail": "Voucher not found", "support_id": "a1b2c3d4"}}},
        },
        409: {
            "description": "Conflict with an existing voucher",
            "content": {
                "application/json": {"example": {"detail": "A voucher with this code already exists", "support_id": "a1b2c3d4"}}
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid request. Please check your input and try again.", "support_id": "a1b2c3d4"}
                }
            },
        },
    },
)
async def update_voucher(
    voucher_id: int,
    voucher_in: VoucherUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("vouchers:update"))],
    voucher_service: VoucherServiceDep,
) -> dict[str, Any]:
    try:
        return await voucher_service.update(db, voucher_id, voucher_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/{voucher_id}",
    status_code=204,
    summary="Delete Voucher",
    description="Soft-delete a voucher.",
    responses={
        204: {"description": "Voucher deleted successfully"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Voucher not found",
            "content": {"application/json": {"example": {"detail": "Voucher not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_voucher(
    voucher_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("vouchers:delete"))],
    voucher_service: VoucherServiceDep,
) -> None:
    await voucher_service.delete(db, voucher_id)
