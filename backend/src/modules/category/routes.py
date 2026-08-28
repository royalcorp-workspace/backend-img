import uuid
from typing import Annotated, Any
from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...infrastructure.auth.dependencies import get_current_user
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import CategoryServiceDep
from .schemas import CategoryCreate, CategoryRead, CategoryUpdate
router = APIRouter(tags=['Categories'])

CATEGORY_EXAMPLE = {
    "id": "019f5935-9e01-7256-81e8-23c114d2eaa4",
    "name": "Kasur & Spring Bed",
    "slug": "kasur-spring-bed",
    "parent_id": None,
    "description": "Berbagai pilihan kasur dan spring bed berkualitas untuk kenyamanan tidur Anda.",
    "tagline": "Tidur Nyenyak, Bangun Segar",
    "image": "https://cms.domain.com/storage/categories/kasur-spring-bed.jpg",
    "banner": "https://cms.domain.com/storage/categories/banner-kasur.jpg",
    "sort_order": 1,
    "status": True,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-08-01T00:00:00"
}


@router.get('/', response_model=PaginatedListResponse[CategoryRead], summary='List Categories', description='Get a paginated list of all categories.', responses={200: {'description': 'A paginated list of categories.', 'content': {'application/json': {'example': {'data': [{'id': 1, 'name': 'Electronics', 'slug': 'electronics', 'parent_id': None, 'description': 'Electronic devices and accessories', 'sort_order': 0, 'status': True, 'created_at': '2026-01-01T00:00:00', 'updated_at': None}], 'total_count': 1, 'has_more': False, 'page': 1, 'items_per_page': 10}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}})
async def list_categories(db: AsyncSessionDep, current_user: Annotated[dict[str, Any], Depends(get_current_user)], category_service: CategoryServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await category_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/flat', response_model=list[CategoryRead], summary='List Categories (Flat)', description='Get a flat list of all categories.', responses={200: {'description': 'A flat list of categories.', 'content': {'application/json': {'example': [{'id': 1, 'name': 'Electronics', 'slug': 'electronics', 'parent_id': None, 'description': 'Electronic devices and accessories', 'sort_order': 0, 'status': True, 'created_at': '2026-01-01T00:00:00', 'updated_at': None}]}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}})
async def list_categories_flat(db: AsyncSessionDep, current_user: Annotated[dict[str, Any], Depends(get_current_user)], category_service: CategoryServiceDep) -> list[Any]:
    return await category_service.get_flat(db)

@router.get('/{category_id}', response_model=CategoryRead, summary='Get Category', description='Get a single category by ID.', responses={200: {'description': 'The requested category.', 'content': {'application/json': {'example': {'id': 1, 'name': 'Electronics', 'slug': 'electronics', 'parent_id': None, 'description': 'Electronic devices and accessories', 'sort_order': 0, 'status': True, 'created_at': '2026-01-01T00:00:00', 'updated_at': None}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}, 404: {'description': 'Category not found', 'content': {'application/json': {'example': {'detail': 'Category not found', 'support_id': 'a1b2c3d4'}}}}})
async def get_category(category_id: uuid.UUID, db: AsyncSessionDep, current_user: Annotated[dict[str, Any], Depends(get_current_user)], category_service: CategoryServiceDep) -> dict[str, Any]:
    return await category_service.get_by_id(db, category_id)