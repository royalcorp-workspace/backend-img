from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import CategoryServiceDep
from .schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(tags=["Categories"])


@router.get(
    "/",
    response_model=PaginatedListResponse[CategoryRead],
    summary="List Categories",
    description="Get a paginated list of all categories.",
    responses={
        200: {
            "description": "A paginated list of categories.",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": 1,
                                "name": "Electronics",
                                "slug": "electronics",
                                "parent_id": None,
                                "description": "Electronic devices and accessories",
                                "sort_order": 0,
                                "status": True,
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
async def list_categories(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("categories:read"))],
    category_service: CategoryServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await category_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/flat",
    response_model=list[CategoryRead],
    summary="List Categories (Flat)",
    description="Get a flat list of all categories.",
    responses={
        200: {
            "description": "A flat list of categories.",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "Electronics",
                            "slug": "electronics",
                            "parent_id": None,
                            "description": "Electronic devices and accessories",
                            "sort_order": 0,
                            "status": True,
                            "created_at": "2026-01-01T00:00:00",
                            "updated_at": None,
                        }
                    ]
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
async def list_categories_flat(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("categories:read"))],
    category_service: CategoryServiceDep,
) -> list[Any]:
    return await category_service.get_flat(db)


@router.post(
    "/",
    response_model=CategoryRead,
    status_code=201,
    summary="Create Category",
    description="Create a new category.",
    responses={
        201: {
            "description": "The created category.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Electronics",
                        "slug": "electronics",
                        "parent_id": None,
                        "description": "Electronic devices and accessories",
                        "sort_order": 0,
                        "status": True,
                        "created_at": "2026-01-01T00:00:00",
                        "updated_at": None,
                    }
                }
            },
        },
        400: {
            "description": "Bad request",
            "content": {
                "application/json": {"example": {"detail": "Invalid category data provided", "support_id": "a1b2c3d4"}}
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
        409: {
            "description": "Conflict with an existing category",
            "content": {
                "application/json": {
                    "example": {"detail": "A category with this slug already exists", "support_id": "a1b2c3d4"}
                }
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
async def create_category(
    category_in: CategoryCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("categories:create"))],
    category_service: CategoryServiceDep,
) -> dict[str, Any]:
    try:
        return await category_service.create(category_in, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Get Category",
    description="Get a single category by ID.",
    responses={
        200: {
            "description": "The requested category.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Electronics",
                        "slug": "electronics",
                        "parent_id": None,
                        "description": "Electronic devices and accessories",
                        "sort_order": 0,
                        "status": True,
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
            "description": "Category not found",
            "content": {"application/json": {"example": {"detail": "Category not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def get_category(
    category_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("categories:read"))],
    category_service: CategoryServiceDep,
) -> dict[str, Any]:
    return await category_service.get_by_id(db, category_id)


@router.put(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Update Category",
    description="Update an existing category.",
    responses={
        200: {
            "description": "The updated category.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Electronics",
                        "slug": "electronics",
                        "parent_id": None,
                        "description": "Electronic devices and accessories",
                        "sort_order": 0,
                        "status": True,
                        "created_at": "2026-01-01T00:00:00",
                        "updated_at": None,
                    }
                }
            },
        },
        400: {
            "description": "Bad request",
            "content": {
                "application/json": {"example": {"detail": "Invalid category data provided", "support_id": "a1b2c3d4"}}
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
            "description": "Category not found",
            "content": {"application/json": {"example": {"detail": "Category not found", "support_id": "a1b2c3d4"}}},
        },
        409: {
            "description": "Conflict with an existing category",
            "content": {
                "application/json": {
                    "example": {"detail": "A category with this slug already exists", "support_id": "a1b2c3d4"}
                }
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
async def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("categories:update"))],
    category_service: CategoryServiceDep,
) -> dict[str, Any]:
    try:
        return await category_service.update(db, category_id, category_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/{category_id}",
    status_code=204,
    summary="Delete Category",
    description="Soft-delete a category.",
    responses={
        204: {"description": "Category deleted successfully"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Category not found",
            "content": {"application/json": {"example": {"detail": "Category not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_category(
    category_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("categories:delete"))],
    category_service: CategoryServiceDep,
) -> None:
    await category_service.delete(db, category_id)
