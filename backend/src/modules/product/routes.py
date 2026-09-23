import asyncio
from typing import Annotated, Any
from uuid import UUID
import httpx
from fastapi import APIRouter, Body, Depends, Header, Query, Request
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.config import get_settings
from ...infrastructure.dependencies import AsyncSessionDep
from ...infrastructure.logging import get_logger
from ...infrastructure.auth.dependencies import get_current_user
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from ..review.schemas import ProductReviewsRead
from .dependencies import ColorServiceDep, ImageServiceDep, ProductServiceDep, VariantServiceDep
from sqlalchemy import select
from ..common.utils import get_media_url
from .models import Product, ProductBundling, ProductBundlingItem
from .schemas import (
    ProductBundlingDetailRead,
    ProductBundlingRead,
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
router = APIRouter(tags=['Products'])
logger = get_logger()

PRODUCT_EXAMPLE = {
    "id": "25043f8a-7517-4caa-a8bb-144e8e6e7a78",
    "name": "KB GRAND X LB-17",
    "slug": "kb-grand-x-lb-17-nmpb",
    "category_id": "0c7c1906-a7d8-40a5-b0fe-ae2dfaca378e",
    "thumbnail": "https://cms.domain.com/storage/products/kb-grand.jpg",
    "alt_text": "Kasur Busa Grand",
    "short_description": "Kasur Busa Berkualitas",
    "description": "Kasur busa dengan density tinggi, awet dan tidak mudah kempes.",
    "base_price": 1250000.0,
    "segments": {
        "uom": "PC",
        "segment1": "KB",
        "segment2": "GRAND"
    },
    "best_seller": True,
    "is_new": False,
    "sort_order": 1,
    "status": True,
    "images": [
        {
            "id": "99043f8a-7517-4caa-a8bb-144e8e6e7a99",
            "product_id": "25043f8a-7517-4caa-a8bb-144e8e6e7a78",
            "image": "https://cms.domain.com/storage/products/kb-grand-2.jpg",
            "alt_text": "Kasur Busa Grand Side",
            "status": True
        }
    ],
    "variants": [
        {
            "id": "88043f8a-7517-4caa-a8bb-144e8e6e7a88",
            "product_id": "25043f8a-7517-4caa-a8bb-144e8e6e7a78",
            "sku": "KBGRAND120200",
            "variant_name": "120 x 200 cm",
            "width": 120.0,
            "length": 200.0,
            "height": 20.0,
            "weight": 15.0,
            "sell_price": 1250000.0,
            "base_price": 1250000.0,
            "status": True
        }
    ],
    "colors": [
        {
            "id": "77043f8a-7517-4caa-a8bb-144e8e6e7a77",
            "product_id": "25043f8a-7517-4caa-a8bb-144e8e6e7a78",
            "color_name": "Merah",
            "color_code": "RED",
            "status": True
        }
    ],
    "price_product_settings": [],
    "reviews": [],
    "avg_rating": 4.8,
    "total_reviews": 15
}


@router.get('/', response_model=PaginatedListResponse[ProductRead], summary='List Products', description='Get a paginated list of products with optional filters.', responses={200: {'description': 'Paginated list of products', 'content': {'application/json': {'example': {'data': [{'id': 1, 'name': 'DV (L1) HOTEL CLASSIC LH-8', 'slug': 'dvl100220010607', 'category_id': 3, 'thumbnail': 'https://example.com/images/dvl100220010607.jpg', 'alt_text': 'DV (L1) HOTEL CLASSIC LH-8 Image', 'short_description': '200 X 090', 'description': 'Produk disinkronkan dari POS JDE: DV (L1) HOTEL CLASSIC LH-8', 'base_price': 0.0, 'segments': {'uom': 'PC', 'segment1': 'DV', 'segment2': 'L1002200', 'segment3': '10607', 'segment4': 'S', 'segment5': '200', 'segment6': '090', 'segment7': '', 'segment8': '', 'segment9': '', 'segment10': '', 'base_price': 0}, 'best_seller': True, 'is_new': False, 'sort_order': 1, 'status': True, 'images': [{'id': 1, 'product_id': 1, 'image': 'https://example.com/images/dvl100220010607.jpg', 'alt_text': 'DV (L1) HOTEL CLASSIC LH-8 Image', 'status': True}], 'variants': [{'id': 1, 'product_id': 1, 'sku': 'DVL100220010607S200090', 'variant_name': '200 X 090', 'width': 90.0, 'length': 200.0, 'height': 0.0, 'weight': 0.0, 'price': 0.0, 'status': True, 'price_product_settings': []}], 'colors': [{'id': 1, 'product_id': 1, 'color_name': 'Fabric 10607', 'color_code': '10607', 'status': True}], 'price_product_settings': [{'id': 1, 'title': 'Diskon Weekend', 'code': 'WEEKEND10', 'discount_type': 1, 'discount_value': 10.0, 'max_discount': 50000.0, 'min_purchase': 0.0, 'is_active': True}], 'reviews': [], 'avg_rating': 0.0, 'total_reviews': 0}], 'total_count': 1, 'has_more': False, 'page': 1, 'items_per_page': 10}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}})
async def list_products(db: AsyncSessionDep, current_user: Annotated[dict[str, Any], Depends(get_current_user)], product_service: ProductServiceDep, page: int=1, items_per_page: int=10, category_id: UUID | None=None, status: int | None=None, best_seller: bool | None=None, is_new: bool | None=None, search: str | None=None) -> dict[str, Any]:
    filters = {}
    if category_id is not None:
        filters['category_id'] = category_id
    if status is not None:
        filters['status'] = status
    if best_seller is not None:
        filters['best_seller'] = best_seller
    if is_new is not None:
        filters['is_new'] = is_new
    if search:
        filters['name__ilike'] = f'%{search}%'
    crud_data = await product_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page, **filters)
    return paginated_response(crud_data=crud_data, page=page, items_per_page=items_per_page)

@router.get('/bundlings', response_model=dict, summary='List Active Product Bundlings', description='Get all active product bundlings with their items.')
async def get_bundlings(db: AsyncSessionDep):
    try:
        stmt = select(ProductBundling).where(ProductBundling.deleted == False, ProductBundling.is_active == True)
        result = await db.execute(stmt)
        bundlings = result.scalars().all()
        formatted = []
        for b in bundlings:
            total_normal_price = 0.0
            for item in (b.items or []):
                var = item.variant
                prod = item.product
                p_price = float(var.sell_price if var and var.sell_price else (prod.base_price if prod and prod.base_price else 0.0))
                if not item.is_suggest:
                    total_normal_price += p_price * (item.quantity or 1)
            b_price = float(b.price or 0.0)
            formatted.append({
                "id": str(b.id),
                "name": b.name,
                "slug": b.slug,
                "description": b.description,
                "price": b_price,
                "total_normal_price": total_normal_price,
                "is_active": b.is_active,
                "image_url": get_media_url(b.image_url),
                "banner_image": get_media_url(b.banner_image),
                "total_items": len(b.items or []),
            })
        return {'success': True, 'data': formatted}
    except Exception as e:
        logger.error(f'Error fetching bundlings: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=f'Failed to fetch bundlings: {str(e)}')


@router.get('/bundlings/{id_or_slug}', response_model=dict, summary='Get Product Bundling Detail', description='Get a single product bundling by UUID or slug with full item breakdown and suggested add-ons.')
async def get_bundling_detail(id_or_slug: str, db: AsyncSessionDep):
    try:
        is_uuid = False
        parsed_uuid = None
        try:
            parsed_uuid = UUID(id_or_slug)
            is_uuid = True
        except ValueError:
            is_uuid = False

        if is_uuid:
            stmt = select(ProductBundling).where(ProductBundling.id == parsed_uuid, ProductBundling.deleted == False)
        else:
            stmt = select(ProductBundling).where(ProductBundling.slug == id_or_slug, ProductBundling.deleted == False)

        result = await db.execute(stmt)
        bundling = result.scalars().first()

        # Fallback: check Product table if created as is_bundle = True
        if not bundling:
            if is_uuid:
                prod_stmt = select(Product).where(Product.id == parsed_uuid, Product.is_bundle == True, Product.deleted == False)
            else:
                prod_stmt = select(Product).where(Product.slug == id_or_slug, Product.is_bundle == True, Product.deleted == False)
            prod_res = await db.execute(prod_stmt)
            prod_bundle = prod_res.scalars().first()
            if prod_bundle:
                item_stmt = select(ProductBundlingItem).where(ProductBundlingItem.bundling_id == prod_bundle.id)
                item_res = await db.execute(item_stmt)
                b_items = item_res.scalars().all()
                bundling = ProductBundling(
                    id=prod_bundle.id,
                    name=prod_bundle.name,
                    slug=prod_bundle.slug,
                    description=prod_bundle.description,
                    price=float(prod_bundle.base_price or 0.0),
                    is_active=bool(prod_bundle.status),
                    image_url=prod_bundle.thumbnail,
                )
                bundling.items = b_items

        if not bundling:
            raise HTTPException(status_code=404, detail="Product bundling not found")

        items_data = []
        fixed_items = []
        suggest_items = []
        total_normal_price = 0.0

        for item in (bundling.items or []):
            prod = item.product
            var = item.variant
            
            prod_variants = [v for v in (prod.variants if prod and hasattr(prod, 'variants') and prod.variants else []) if not getattr(v, 'deleted', False) and (getattr(v, 'sell_price', 0) or 0) > 0]
            if var and var.sell_price:
                p_orig_price = float(var.sell_price)
                min_p = p_orig_price
                max_p = p_orig_price
            elif prod_variants:
                prices = [float(v.sell_price) for v in prod_variants if v.sell_price]
                min_p = min(prices) if prices else 0.0
                max_p = max(prices) if prices else 0.0
                p_orig_price = min_p
            else:
                p_orig_price = float(prod.base_price or 0.0) if prod else 0.0
                min_p = p_orig_price
                max_p = p_orig_price

            range_text = f"Rp {int(min_p):,} - Rp {int(max_p):,}".replace(",", ".") if min_p < max_p else f"Rp {int(min_p):,}".replace(",", ".")

            item_qty = item.quantity or 1
            if not item.is_suggest:
                total_normal_price += p_orig_price * item_qty

            bundle_item_price = float(item.bundle_price) if item.bundle_price is not None else None
            disc_percent = float(item.discount_percent) if item.discount_percent is not None else None
            disc_nominal = float(item.discount_nominal) if item.discount_nominal is not None else None

            if disc_percent and not bundle_item_price:
                bundle_item_price = round(p_orig_price * (1 - (disc_percent / 100.0)), 2)

            item_dict = {
                "id": str(item.id),
                "bundling_id": str(bundling.id),
                "product_id": str(item.product_id),
                "variant_id": str(item.variant_id) if item.variant_id else None,
                "product_name": prod.name if prod else None,
                "product_slug": prod.slug if prod else None,
                "variant_name": var.variant_name if var else None,
                "sku": var.sku if var else None,
                "quantity": item_qty,
                "is_suggest": item.is_suggest,
                "bundle_price": bundle_item_price,
                "discount_percent": disc_percent,
                "discount_nominal": disc_nominal,
                "original_price": p_orig_price,
                "min_price": min_p,
                "max_price": max_p,
                "price_range_text": range_text,
                "image_url": get_media_url(var.image_url if var and hasattr(var, 'image_url') and var.image_url else (prod.thumbnail if prod and prod.thumbnail else (prod.images[0].image if prod and prod.images else None))),
            }
            items_data.append(item_dict)
            if item.is_suggest:
                suggest_items.append(item_dict)
            else:
                fixed_items.append(item_dict)

        bundle_price = float(bundling.price or 0.0)
        discount_amount = max(0.0, total_normal_price - bundle_price) if total_normal_price > bundle_price else 0.0
        discount_percent = round((discount_amount / total_normal_price) * 100.0, 1) if total_normal_price > 0 else 0.0

        data = {
            "id": str(bundling.id),
            "name": bundling.name,
            "slug": bundling.slug,
            "description": bundling.description,
            "price": bundle_price,
            "total_normal_price": total_normal_price,
            "discount_amount": discount_amount,
            "discount_percent": discount_percent,
            "is_active": bundling.is_active,
            "banner_image": get_media_url(bundling.banner_image if hasattr(bundling, 'banner_image') else None),
            "image_url": get_media_url(bundling.image_url),
            "items": items_data,
            "fixed_items": fixed_items,
            "suggest_items": suggest_items,
        }
        return {"success": True, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error fetching bundling detail: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=f'Failed to fetch bundling detail: {str(e)}')


@router.get('/{product_id}/reviews', response_model=ProductReviewsRead, summary='List Reviews', description='Get reviews for a product.', responses={200: {'description': 'Product reviews', 'content': {'application/json': {'example': {'reviews': [], 'avg_rating': 0.0, 'total_reviews': 0}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}, 404: {'description': 'Product not found', 'content': {'application/json': {'example': {'detail': 'Product not found', 'support_id': 'a1b2c3d4'}}}}})
async def list_product_reviews(product_id: UUID, db: AsyncSessionDep, current_user: Annotated[dict[str, Any], Depends(get_current_user)], product_service: ProductServiceDep) -> Any:
    product = await product_service.get_by_id(db, product_id)
    reviews = product.get('reviews', [])
    avg_rating = sum((r['rating'] for r in reviews if r.get('rating'))) / len(reviews) if reviews else 0
    return {'reviews': reviews, 'avg_rating': round(avg_rating, 2), 'total_reviews': len(reviews)}


@router.get('/{product_id}', response_model=ProductRead, summary='Get Product', description='Get a single product by ID.', responses={200: {'description': 'Product details', 'content': {'application/json': {'example': {'id': 1, 'name': 'DV (L1) HOTEL CLASSIC LH-8', 'slug': 'dvl100220010607', 'category_id': 3, 'thumbnail': 'https://example.com/images/dvl100220010607.jpg', 'alt_text': 'DV (L1) HOTEL CLASSIC LH-8 Image', 'short_description': '200 X 090', 'description': 'Produk disinkronkan dari POS JDE: DV (L1) HOTEL CLASSIC LH-8', 'base_price': 0.0, 'segments': {'uom': 'PC', 'segment1': 'DV', 'segment2': 'L1002200', 'segment3': '10607', 'segment4': 'S', 'segment5': '200', 'segment6': '090', 'segment7': '', 'segment8': '', 'segment9': '', 'segment10': '', 'base_price': 0}, 'best_seller': True, 'is_new': False, 'sort_order': 1, 'status': True, 'images': [{'id': 1, 'product_id': 1, 'image': 'https://example.com/images/dvl100220010607.jpg', 'alt_text': 'DV (L1) HOTEL CLASSIC LH-8 Image', 'status': True}], 'variants': [{'id': 1, 'product_id': 1, 'sku': 'DVL100220010607S200090', 'variant_name': '200 X 090', 'width': 90.0, 'length': 200.0, 'height': 0.0, 'weight': 0.0, 'price': 0.0, 'status': True, 'price_product_settings': []}], 'colors': [{'id': 1, 'product_id': 1, 'color_name': 'Fabric 10607', 'color_code': '10607', 'status': True}], 'price_product_settings': [{'id': 1, 'title': 'Diskon Weekend', 'code': 'WEEKEND10', 'discount_type': 1, 'discount_value': 10.0, 'max_discount': 50000.0, 'min_purchase': 0.0, 'is_active': True}], 'reviews': [], 'avg_rating': 0.0, 'total_reviews': 0}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}, 404: {'description': 'Product not found', 'content': {'application/json': {'example': {'detail': 'Product not found', 'support_id': 'a1b2c3d4'}}}}})
async def get_product(product_id: UUID, db: AsyncSessionDep, current_user: Annotated[dict[str, Any], Depends(get_current_user)], product_service: ProductServiceDep) -> dict[str, Any]:
    return await product_service.get_by_id(db, product_id)