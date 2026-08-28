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
from .schemas import ProductColorCreate, ProductColorRead, ProductCreate, ProductImageCreate, ProductImageRead, ProductRead, ProductUpdate, ProductVariantCreate, ProductVariantRead, ProductBundlingRead
from .sync import logger as sync_logger
from .sync import sync_pos_products_task, sync_products_data
router = APIRouter(tags=['Products'])
logger = get_logger()

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

@router.get('/{product_id}/reviews', response_model=ProductReviewsRead, summary='List Reviews', description='Get reviews for a product.', responses={200: {'description': 'Product reviews', 'content': {'application/json': {'example': {'reviews': [], 'avg_rating': 0.0, 'total_reviews': 0}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}, 404: {'description': 'Product not found', 'content': {'application/json': {'example': {'detail': 'Product not found', 'support_id': 'a1b2c3d4'}}}}})
async def list_product_reviews(product_id: UUID, db: AsyncSessionDep, current_user: Annotated[dict[str, Any], Depends(get_current_user)], product_service: ProductServiceDep) -> Any:
    product = await product_service.get_by_id(db, product_id)
    reviews = product.get('reviews', [])
    avg_rating = sum((r['rating'] for r in reviews if r.get('rating'))) / len(reviews) if reviews else 0
    return {'reviews': reviews, 'avg_rating': round(avg_rating, 2), 'total_reviews': len(reviews)}

@router.get('/{product_id}', response_model=ProductRead, summary='Get Product', description='Get a single product by ID.', responses={200: {'description': 'Product details', 'content': {'application/json': {'example': {'id': 1, 'name': 'DV (L1) HOTEL CLASSIC LH-8', 'slug': 'dvl100220010607', 'category_id': 3, 'thumbnail': 'https://example.com/images/dvl100220010607.jpg', 'alt_text': 'DV (L1) HOTEL CLASSIC LH-8 Image', 'short_description': '200 X 090', 'description': 'Produk disinkronkan dari POS JDE: DV (L1) HOTEL CLASSIC LH-8', 'base_price': 0.0, 'segments': {'uom': 'PC', 'segment1': 'DV', 'segment2': 'L1002200', 'segment3': '10607', 'segment4': 'S', 'segment5': '200', 'segment6': '090', 'segment7': '', 'segment8': '', 'segment9': '', 'segment10': '', 'base_price': 0}, 'best_seller': True, 'is_new': False, 'sort_order': 1, 'status': True, 'images': [{'id': 1, 'product_id': 1, 'image': 'https://example.com/images/dvl100220010607.jpg', 'alt_text': 'DV (L1) HOTEL CLASSIC LH-8 Image', 'status': True}], 'variants': [{'id': 1, 'product_id': 1, 'sku': 'DVL100220010607S200090', 'variant_name': '200 X 090', 'width': 90.0, 'length': 200.0, 'height': 0.0, 'weight': 0.0, 'price': 0.0, 'status': True, 'price_product_settings': []}], 'colors': [{'id': 1, 'product_id': 1, 'color_name': 'Fabric 10607', 'color_code': '10607', 'status': True}], 'price_product_settings': [{'id': 1, 'title': 'Diskon Weekend', 'code': 'WEEKEND10', 'discount_type': 1, 'discount_value': 10.0, 'max_discount': 50000.0, 'min_purchase': 0.0, 'is_active': True}], 'reviews': [], 'avg_rating': 0.0, 'total_reviews': 0}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}, 404: {'description': 'Product not found', 'content': {'application/json': {'example': {'detail': 'Product not found', 'support_id': 'a1b2c3d4'}}}}})
async def get_product(product_id: UUID, db: AsyncSessionDep, current_user: Annotated[dict[str, Any], Depends(get_current_user)], product_service: ProductServiceDep) -> dict[str, Any]:
    return await product_service.get_by_id(db, product_id)
from sqlalchemy import select
from .models import ProductBundling

@router.get('/bundlings', response_model=dict, summary='List Active Product Bundlings', description='Get all active product bundlings with their items.')
async def get_bundlings(db: AsyncSessionDep):
    try:
        stmt = select(ProductBundling).where(ProductBundling.deleted == False, ProductBundling.is_active == True)
        result = await db.execute(stmt)
        bundlings = result.scalars().all()
        return {'success': True, 'data': bundlings}
    except Exception as e:
        logger.error(f'Error fetching bundlings: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=f'Failed to fetch bundlings: {str(e)}')