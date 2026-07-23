import asyncio
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Body, Depends, Header, Query, Request
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.config import get_settings
from ...infrastructure.dependencies import (
    AsyncSessionDep,
)
from ...infrastructure.logging import get_logger
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from ..review.schemas import ProductReviewsRead
from .dependencies import (
    ColorServiceDep,
    ImageServiceDep,
    ProductServiceDep,
    VariantServiceDep,
)
from .schemas import (
    ProductColorCreate,
    ProductColorRead,
    ProductCreate,
    ProductImageCreate,
    ProductImageRead,
    ProductRead,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantRead,
)
from .sync import logger as sync_logger
from .sync import sync_pos_products_task, sync_products_data

router = APIRouter(tags=["Products"])
logger = get_logger()


@router.get(
    "/",
    response_model=PaginatedListResponse[ProductRead],
    summary="List Products",
    description="Get a paginated list of products with optional filters.",
    responses={
        200: {
            "description": "Paginated list of products",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
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
                                    "segment6": "090",
                                    "segment7": "",
                                    "segment8": "",
                                    "segment9": "",
                                    "segment10": "",
                                    "base_price": 0
                                },
                                "best_seller": True,
                                "is_new": False,
                                "sort_order": 1,
                                "status": True,
                                "images": [
                                    {
                                        "id": 1,
                                        "product_id": 1,
                                        "image": "https://example.com/images/dvl100220010607.jpg",
                                        "alt_text": "DV (L1) HOTEL CLASSIC LH-8 Image",
                                        "status": True
                                    }
                                ],
                                "variants": [
                                    {
                                        "id": 1,
                                        "product_id": 1,
                                        "sku": "DVL100220010607S200090",
                                        "variant_name": "200 X 090",
                                        "width": 90.0,
                                        "length": 200.0,
                                        "height": 0.0,
                                        "weight": 0.0,
                                        "price": 0.0,
                                        "status": True,
                                        "price_product_settings": []
                                    }
                                ],
                                "colors": [
                                    {
                                        "id": 1,
                                        "product_id": 1,
                                        "color_name": "Fabric 10607",
                                        "color_code": "10607",
                                        "status": True
                                    }
                                ],
                                "price_product_settings": [
                                    {
                                        "id": 1,
                                        "title": "Diskon Weekend",
                                        "code": "WEEKEND10",
                                        "discount_type": 1,
                                        "discount_value": 10.0,
                                        "max_discount": 50000.0,
                                        "min_purchase": 0.0,
                                        "is_active": True
                                    }
                                ],
                                "reviews": [],
                                "avg_rating": 0.0,
                                "total_reviews": 0,
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
async def list_products(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:read"))],
    product_service: ProductServiceDep,
    page: int = 1,
    items_per_page: int = 10,
    category_id: UUID | None = None,
    status: int | None = None,
    best_seller: bool | None = None,
    is_new: bool | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    filters = {}
    if category_id is not None:
        filters["category_id"] = category_id
    if status is not None:
        filters["status"] = status
    if best_seller is not None:
        filters["best_seller"] = best_seller
    if is_new is not None:
        filters["is_new"] = is_new
    if search:
        filters["name__ilike"] = f"%{search}%"
    crud_data = await product_service.get_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page, **filters
    )
    return paginated_response(crud_data=crud_data, page=page, items_per_page=items_per_page)


@router.get(
    "/{product_id}/reviews",
    response_model=ProductReviewsRead,
    summary="List Reviews",
    description="Get reviews for a product.",
    responses={
        200: {
            "description": "Product reviews",
            "content": {"application/json": {"example": {"reviews": [], "avg_rating": 0.0, "total_reviews": 0}}},
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
            "description": "Product not found",
            "content": {"application/json": {"example": {"detail": "Product not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def list_product_reviews(
    product_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:read"))],
    product_service: ProductServiceDep,
) -> Any:
    product = await product_service.get_by_id(db, product_id)
    reviews = product.get("reviews", [])
    avg_rating = sum(r["rating"] for r in reviews if r.get("rating")) / len(reviews) if reviews else 0
    return {
        "reviews": reviews,
        "avg_rating": round(avg_rating, 2),
        "total_reviews": len(reviews),
    }


@router.post(
    "/",
    response_model=ProductRead,
    status_code=201,
    summary="Create Product",
    description="Create a new product.",
    responses={
        201: {
            "description": "Product created",
            "content": {
                "application/json": {
                    "example": {
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
                            "segment6": "090",
                            "segment7": "",
                            "segment8": "",
                            "segment9": "",
                            "segment10": "",
                            "base_price": 0
                        },
                        "best_seller": True,
                        "is_new": False,
                        "sort_order": 1,
                        "status": True,
                        "images": [
                            {
                                "id": 1,
                                "product_id": 1,
                                "image": "https://example.com/images/dvl100220010607.jpg",
                                "alt_text": "DV (L1) HOTEL CLASSIC LH-8 Image",
                                "status": True
                            }
                        ],
                        "variants": [
                            {
                                "id": 1,
                                "product_id": 1,
                                "sku": "DVL100220010607S200090",
                                "variant_name": "200 X 090",
                                "width": 90.0,
                                "length": 200.0,
                                "height": 0.0,
                                "weight": 0.0,
                                "price": 0.0,
                                "status": True,
                                "price_product_settings": []
                            }
                        ],
                        "colors": [
                            {
                                "id": 1,
                                "product_id": 1,
                                "color_name": "Fabric 10607",
                                "color_code": "10607",
                                "status": True
                            }
                        ],
                        "price_product_settings": [
                            {
                                "id": 1,
                                "title": "Diskon Weekend",
                                "code": "WEEKEND10",
                                "discount_type": 1,
                                "discount_value": 10.0,
                                "max_discount": 50000.0,
                                "min_purchase": 0.0,
                                "is_active": True
                            }
                        ],
                        "reviews": [],
                        "avg_rating": 0.0,
                        "total_reviews": 0,
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
        409: {
            "description": "Duplicate slug",
            "content": {"application/json": {"example": {"detail": "Duplicate slug", "support_id": "a1b2c3d4"}}},
        },
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:create"))],
    product_service: ProductServiceDep,
) -> dict[str, Any]:
    try:
        return await product_service.create(product_in, db)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    summary="Get Product",
    description="Get a single product by ID.",
    responses={
        200: {
            "description": "Product details",
            "content": {
                "application/json": {
                    "example": {
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
                            "segment6": "090",
                            "segment7": "",
                            "segment8": "",
                            "segment9": "",
                            "segment10": "",
                            "base_price": 0
                        },
                        "best_seller": True,
                        "is_new": False,
                        "sort_order": 1,
                        "status": True,
                        "images": [
                            {
                                "id": 1,
                                "product_id": 1,
                                "image": "https://example.com/images/dvl100220010607.jpg",
                                "alt_text": "DV (L1) HOTEL CLASSIC LH-8 Image",
                                "status": True
                            }
                        ],
                        "variants": [
                            {
                                "id": 1,
                                "product_id": 1,
                                "sku": "DVL100220010607S200090",
                                "variant_name": "200 X 090",
                                "width": 90.0,
                                "length": 200.0,
                                "height": 0.0,
                                "weight": 0.0,
                                "price": 0.0,
                                "status": True,
                                "price_product_settings": []
                            }
                        ],
                        "colors": [
                            {
                                "id": 1,
                                "product_id": 1,
                                "color_name": "Fabric 10607",
                                "color_code": "10607",
                                "status": True
                            }
                        ],
                        "price_product_settings": [
                            {
                                "id": 1,
                                "title": "Diskon Weekend",
                                "code": "WEEKEND10",
                                "discount_type": 1,
                                "discount_value": 10.0,
                                "max_discount": 50000.0,
                                "min_purchase": 0.0,
                                "is_active": True
                            }
                        ],
                        "reviews": [],
                        "avg_rating": 0.0,
                        "total_reviews": 0,
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
            "description": "Product not found",
            "content": {"application/json": {"example": {"detail": "Product not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def get_product(
    product_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:read"))],
    product_service: ProductServiceDep,
) -> dict[str, Any]:
    return await product_service.get_by_id(db, product_id)


@router.put(
    "/{product_id}",
    response_model=ProductRead,
    summary="Update Product",
    description="Update an existing product.",
    responses={
        200: {
            "description": "Product updated",
            "content": {
                "application/json": {
                    "example": {
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
                            "segment6": "090",
                            "segment7": "",
                            "segment8": "",
                            "segment9": "",
                            "segment10": "",
                            "base_price": 0
                        },
                        "best_seller": True,
                        "is_new": False,
                        "sort_order": 1,
                        "status": True,
                        "images": [
                            {
                                "id": 1,
                                "product_id": 1,
                                "image": "https://example.com/images/dvl100220010607.jpg",
                                "alt_text": "DV (L1) HOTEL CLASSIC LH-8 Image",
                                "status": True
                            }
                        ],
                        "variants": [
                            {
                                "id": 1,
                                "product_id": 1,
                                "sku": "DVL100220010607S200090",
                                "variant_name": "200 X 090",
                                "width": 90.0,
                                "length": 200.0,
                                "height": 0.0,
                                "weight": 0.0,
                                "price": 0.0,
                                "status": True,
                                "price_product_settings": []
                            }
                        ],
                        "colors": [
                            {
                                "id": 1,
                                "product_id": 1,
                                "color_name": "Fabric 10607",
                                "color_code": "10607",
                                "status": True
                            }
                        ],
                        "price_product_settings": [
                            {
                                "id": 1,
                                "title": "Diskon Weekend",
                                "code": "WEEKEND10",
                                "discount_type": 1,
                                "discount_value": 10.0,
                                "max_discount": 50000.0,
                                "min_purchase": 0.0,
                                "is_active": True
                            }
                        ],
                        "reviews": [],
                        "avg_rating": 0.0,
                        "total_reviews": 0,
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
        404: {
            "description": "Product not found",
            "content": {"application/json": {"example": {"detail": "Product not found", "support_id": "a1b2c3d4"}}},
        },
        409: {
            "description": "Duplicate slug",
            "content": {"application/json": {"example": {"detail": "Duplicate slug", "support_id": "a1b2c3d4"}}},
        },
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_product(
    product_id: UUID,
    product_in: ProductUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:update"))],
    product_service: ProductServiceDep,
) -> dict[str, Any]:
    try:
        return await product_service.update(db, product_id, product_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/{product_id}",
    status_code=204,
    summary="Delete Product",
    description="Soft-delete a product.",
    responses={
        204: {"description": "Product deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Product not found",
            "content": {"application/json": {"example": {"detail": "Resource not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_product(
    product_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:delete"))],
    product_service: ProductServiceDep,
) -> None:
    await product_service.delete(db, product_id)


@router.post(
    "/{product_id}/images",
    response_model=ProductImageRead,
    status_code=201,
    summary="Add Product Image",
    description="Add an image to a product.",
    responses={
        201: {
            "description": "Image added",
            "content": {
                "application/json": {
                    "example": {
                        "product_id": 1,
                        "image": "https://example.com/image.jpg",
                        "alt_text": "Product image",
                        "sort_order": 0,
                        "status": True,
                        "id": 1,
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
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def add_product_image(
    product_id: UUID,
    image_in: ProductImageCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:update"))],
    image_service: ImageServiceDep,
) -> dict[str, Any]:
    image_in.product_id = product_id
    return await image_service.create(db, image_in)


@router.delete(
    "/images/{image_id}",
    status_code=204,
    summary="Delete Product Image",
    description="Remove an image from a product.",
    responses={
        204: {"description": "Image deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Image not found",
            "content": {"application/json": {"example": {"detail": "Resource not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_product_image(
    image_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:update"))],
    image_service: ImageServiceDep,
) -> None:
    await image_service.delete(db, image_id)


@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantRead,
    status_code=201,
    summary="Add Product Variant",
    description="Add a variant to a product.",
    responses={
        201: {
            "description": "Variant added",
            "content": {
                "application/json": {
                    "example": {
                        "product_id": 1,
                        "sku": "VAR-001",
                        "variant_name": "Small",
                        "width": 10.0,
                        "length": 10.0,
                        "height": 5.0,
                        "weight": 100.0,
                        "price": 15000.0,
                        "stock_qty": 100,
                        "min_order_qty": 1,
                        "sort_order": 0,
                        "status": True,
                        "id": 1,
                        "price_product_settings": [
                            {
                                "id": 1,
                                "title": "Diskon Weekend",
                                "code": "WEEKEND10",
                                "discount_type": 1,
                                "discount_value": 10.0,
                                "max_discount": 50000.0,
                                "min_purchase": 0.0,
                                "is_active": True
                            }
                        ],
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
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def add_product_variant(
    product_id: UUID,
    variant_in: ProductVariantCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:update"))],
    variant_service: VariantServiceDep,
) -> dict[str, Any]:
    variant_in.product_id = product_id
    return await variant_service.create(db, variant_in)


@router.put(
    "/variants/{variant_id}",
    response_model=ProductVariantRead,
    summary="Update Product Variant",
    description="Update an existing variant.",
    responses={
        200: {
            "description": "Variant updated",
            "content": {
                "application/json": {
                    "example": {
                        "product_id": 1,
                        "sku": "VAR-001",
                        "variant_name": "Small",
                        "width": 10.0,
                        "length": 10.0,
                        "height": 5.0,
                        "weight": 100.0,
                        "price": 15000.0,
                        "stock_qty": 100,
                        "min_order_qty": 1,
                        "sort_order": 0,
                        "status": True,
                        "id": 1,
                        "price_product_settings": [
                            {
                                "id": 1,
                                "title": "Diskon Weekend",
                                "code": "WEEKEND10",
                                "discount_type": 1,
                                "discount_value": 10.0,
                                "max_discount": 50000.0,
                                "min_purchase": 0.0,
                                "is_active": True
                            }
                        ],
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
        404: {
            "description": "Variant not found",
            "content": {"application/json": {"example": {"detail": "Variant not found", "support_id": "a1b2c3d4"}}},
        },
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_product_variant(
    variant_id: UUID,
    variant_in: ProductVariantCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:update"))],
    variant_service: VariantServiceDep,
) -> dict[str, Any]:
    return await variant_service.update(db, variant_id, variant_in)


@router.delete(
    "/variants/{variant_id}",
    status_code=204,
    summary="Delete Product Variant",
    description="Remove a variant from a product.",
    responses={
        204: {"description": "Variant deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Variant not found",
            "content": {"application/json": {"example": {"detail": "Resource not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_product_variant(
    variant_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:update"))],
    variant_service: VariantServiceDep,
) -> None:
    await variant_service.delete(db, variant_id)


@router.post(
    "/{product_id}/colors",
    response_model=ProductColorRead,
    status_code=201,
    summary="Add Product Color",
    description="Add a color to a product.",
    responses={
        201: {
            "description": "Color added",
            "content": {
                "application/json": {
                    "example": {"product_id": 1, "color_name": "Red", "color_code": "#FF0000", "status": True, "id": 1}
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
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def add_product_color(
    product_id: UUID,
    color_in: ProductColorCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:update"))],
    color_service: ColorServiceDep,
) -> dict[str, Any]:
    color_in.product_id = product_id
    return await color_service.create(db, color_in)


@router.put(
    "/colors/{color_id}",
    response_model=ProductColorRead,
    summary="Update Product Color",
    description="Update an existing product color.",
    responses={
        200: {
            "description": "Color updated",
            "content": {
                "application/json": {
                    "example": {"product_id": 1, "color_name": "Red", "color_code": "#FF0000", "status": True, "id": 1}
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
            "description": "Color not found",
            "content": {"application/json": {"example": {"detail": "Color not found", "support_id": "a1b2c3d4"}}},
        },
        422: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"detail": "Validation error", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def update_product_color(
    color_id: UUID,
    color_in: ProductColorCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:update"))],
    color_service: ColorServiceDep,
) -> dict[str, Any]:
    return await color_service.update(db, color_id, color_in)


@router.delete(
    "/colors/{color_id}",
    status_code=204,
    summary="Delete Product Color",
    description="Remove a color from a product.",
    responses={
        204: {"description": "Color deleted"},
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated", "support_id": "a1b2c3d4"}}},
        },
        403: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Not authorized", "support_id": "a1b2c3d4"}}},
        },
        404: {
            "description": "Color not found",
            "content": {"application/json": {"example": {"detail": "Resource not found", "support_id": "a1b2c3d4"}}},
        },
    },
)
async def delete_product_color(
    color_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("products:update"))],
    color_service: ColorServiceDep,
) -> None:
    await color_service.delete(db, color_id)


@router.post(
    "/webhook-sync",
    openapi_extra={"security": []},
    summary="Receiver Webhook Sync Produk POS",
    description="""
    Menerima payload JSON untuk sinkronisasi produk secara async (background task) atau sync.
    Menangani timeout (waiting time) koneksi dan eksekusi, serta memverifikasi API Key di header.
    """,
    responses={
        200: {
            "description": "Sinkronisasi produk POS selesai (synchronous).",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "completed",
                        "message": "Sinkronisasi produk POS selesai dijalankan secara synchronous.",
                        "result": {
                            "total_items": 1384,
                            "grouped_products": 1384,
                            "inserted_products": 0,
                            "updated_products": 1384,
                            "inserted_variants": 0,
                            "updated_variants": 5283,
                            "inserted_colors": 0,
                            "inserted_images": 0,
                            "failed_items": 0,
                        },
                    }
                }
            },
        },
        202: {
            "description": "Sinkronisasi produk POS berhasil dijadwalkan di latar belakang (asynchronous).",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "queued",
                        "task_id": "abc123",
                        "message": "Sinkronisasi produk POS telah dijadwalkan di latar belakang menggunakan worker.",
                    }
                }
            },
        },
        400: {
            "description": "Format data tidak valid / Parameter tidak lengkap.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Format payload tidak valid. Tipe data yang diterima: <class 'NoneType'>",
                        "support_id": "a1b2c3d4",
                    }
                }
            },
        },
        401: {
            "description": "API Key tidak valid atau tidak ditemukan.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "API Key tidak valid atau tidak ditemukan di header X-API-Key.",
                        "support_id": "a1b2c3d4",
                    }
                }
            },
        },
        408: {
            "description": "Waktu tunggu habis (Request Timeout) saat mengunduh atau memproses data.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Waktu tunggu habis (Request Timeout) saat menghubungi JDE POS Server.",
                        "support_id": "a1b2c3d4",
                    }
                }
            },
        },
        500: {
            "description": "Kesalahan server internal.",
            "content": {
                "application/json": {
                    "example": {"detail": "Terjadi kesalahan saat sinkronisasi: ...", "support_id": "a1b2c3d4"}
                }
            },
        },
        502: {
            "description": "Kesalahan layanan eksternal (JDE POS Server).",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Gagal mengambil berkas dari JDE POS Server. Server JDE merespons dengan status code: 500",
                        "support_id": "a1b2c3d4",
                    }
                }
            },
        },
    },
)
async def webhook_sync_products(
    request: Request,
    db: AsyncSessionDep,
    body: dict[str, Any] = Body(None),
    file_url: str | None = Query(None, description="URL file data_pos_api_master.json untuk diunduh"),
    sync: bool = Query(False, description="Jalankan secara synchronous (tidak disarankan untuk data besar)"),
    x_api_key: str = Header(..., alias="X-API-Key", description="API Key untuk integrasi JDE"),
) -> dict[str, Any]:
    # Verify API Key
    logger = sync_logger
    logger.info(f"Menerima request webhook sync. Headers: {dict(request.headers)}")
    settings = get_settings()
    if x_api_key != settings.JDE_API_KEY:
        logger.warning(f"Verifikasi API Key gagal. Nilai header X-API-Key: '{x_api_key}'")
        raise HTTPException(
            status_code=401,
            detail="API Key tidak valid atau tidak ditemukan di header X-API-Key.",
        )

    payload = body

    # If no payload is provided in body, pull directly from the external JDE endpoint
    has_jde_keys = any(k.startswith("POS_") for k in payload.keys()) if payload and isinstance(payload, dict) else False
    if not payload or not isinstance(payload, dict) or not (has_jde_keys or "rowset" in payload or "data" in payload):
        jde_url = f"{settings.JDE_BASE_URL.rstrip('/')}/sync/item-master"
        logger.info(f"Tidak ada payload body. Mengambil data dari JDE POS Server: {jde_url}")
        try:
            # Set timeout to handle connection/read waiting time
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    jde_url,
                    headers={"X-API-Key": settings.JDE_API_KEY},
                )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "Gagal mengambil berkas dari JDE POS Server. "
                            f"Server JDE merespons dengan status code: {resp.status_code}"
                        ),
                    )
                payload = resp.json()
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Waktu tunggu habis (Request Timeout) saat menghubungi JDE POS Server.",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Kesalahan koneksi saat menghubungi JDE POS Server: {str(e)}",
            )
        except ValueError:
            raise HTTPException(
                status_code=502,
                detail="Respon dari JDE POS Server bukan JSON yang valid.",
            )

    # Validate JDE payload structure
    if isinstance(payload, dict) and ("rowset" in payload or "data" in payload):
        # Valid direct structure
        pass
    elif isinstance(payload, dict):
        pos_key = next((k for k in payload.keys() if k.startswith("POS_")), None)
        if not pos_key:
            pos_key = next((k for k, v in payload.items() if isinstance(v, dict) and ("rowset" in v or "data" in v)), None)

        if not pos_key:
            logger.warning(f"Validasi payload JDE gagal. Payload keys: {list(payload.keys())}")
            raise HTTPException(
                status_code=400,
                detail=(
                    "Format payload tidak valid. Tidak ditemukan data 'rowset', 'data' atau "
                    f"kunci POS_* dalam response JDE. Kunci response: {list(payload.keys())}"
                ),
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Format payload tidak valid. Tipe data yang diterima: {type(payload)}",
        )

    if sync:
        logger.info("Menjalankan sinkronisasi produk POS secara synchronous...")
        try:
            # Wrap execution in asyncio timeout to handle waiting time/processing timeout
            result = await asyncio.wait_for(sync_products_data(db, payload), timeout=60.0)
            return {
                "success": True,
                "status": "completed",
                "message": "Sinkronisasi produk POS selesai dijalankan secara synchronous.",
                "result": result,
            }
        except asyncio.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Waktu eksekusi sinkronisasi habis (Processing Timeout). Harap jalankan secara asynchronous.",
            )
        except Exception as e:
            logger.error(f"Kesalahan sinkronisasi synchronous: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Terjadi kesalahan saat sinkronisasi: {str(e)}")
    else:
        logger.info("Menjadwalkan sinkronisasi produk POS secara asynchronous...")
        try:
            task = await sync_pos_products_task.kiq(payload)
            return {
                "success": True,
                "status": "queued",
                "task_id": task.task_id,
                "message": "Sinkronisasi produk POS telah dijadwalkan di latar belakang menggunakan worker.",
            }
        except Exception as e:
            logger.error(f"Gagal menjadwalkan background task: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Gagal menjadwalkan sinkronisasi di latar belakang: {str(e)}",
            )
