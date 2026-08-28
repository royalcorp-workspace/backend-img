from typing import Annotated, Any
from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import VoucherServiceDep
from .schemas import VoucherCreate, VoucherRead, VoucherUpdate
router = APIRouter(tags=['Vouchers'])

@router.get('/', response_model=PaginatedListResponse[VoucherRead], summary='List Vouchers', description='Get a paginated list of vouchers.', responses={200: {'description': 'A paginated list of vouchers.', 'content': {'application/json': {'example': {'data': [{'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'code': 'SAVE10', 'title': '10% Off', 'description': '10 percent discount on your order', 'type': 'percentage', 'scope': 'global', 'allow_stacking': False, 'value': 10.0, 'min_purchase': 0.0, 'max_discount': None, 'usage_limit': None, 'usage_limit_per_user': None, 'used_count': 0, 'start_date': '2026-01-01T00:00:00', 'end_date': '2026-12-31T23:59:59', 'valid_for_new_customer': False, 'is_active': True, 'created_at': '2026-01-01T00:00:00', 'updated_at': None}], 'total_count': 1, 'has_more': False, 'page': 1, 'items_per_page': 10}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}})
async def list_vouchers(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('vouchers:read'))], voucher_service: VoucherServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await voucher_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/{voucher_id}', response_model=VoucherRead, summary='Get Voucher', description='Get a single voucher by ID.', responses={200: {'description': 'The requested voucher.', 'content': {'application/json': {'example': {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'code': 'SAVE10', 'title': '10% Off', 'description': '10 percent discount on your order', 'type': 'percentage', 'scope': 'global', 'allow_stacking': False, 'value': 10.0, 'min_purchase': 0.0, 'max_discount': None, 'usage_limit': None, 'usage_limit_per_user': None, 'used_count': 0, 'start_date': '2026-01-01T00:00:00', 'end_date': '2026-12-31T23:59:59', 'valid_for_new_customer': False, 'is_active': True, 'created_at': '2026-01-01T00:00:00', 'updated_at': None}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}, 404: {'description': 'Voucher not found', 'content': {'application/json': {'example': {'detail': 'Voucher not found', 'support_id': 'a1b2c3d4'}}}}})
async def get_voucher(voucher_id: int, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('vouchers:read'))], voucher_service: VoucherServiceDep) -> dict[str, Any]:
    return await voucher_service.get_by_id(db, voucher_id)