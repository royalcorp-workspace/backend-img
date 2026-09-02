from typing import Annotated, Any
from uuid import UUID
from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import PaymentMethodServiceDep
from .schemas import PaymentMethodCreate, PaymentMethodRead, PaymentMethodUpdate

router = APIRouter(tags=['Payment Methods'])

PAYMENT_METHOD_EXAMPLE = {
    'id': '019f5933-08c8-7082-b1cd-7185cff32192',
    'code': 'bca_va',
    'name': 'BCA Virtual Account',
    'type': 1,
    'type_name': 'VA',
    'bank_name': 'BCA',
    'provider': 'Espay',
    'image': 'https://example.com/bca.png',
    'has_charge': True,
    'charge_type': 1,
    'charge_value': 4000.0,
    'charge_bearer': 'customer',
    'minimum_amount': 10000.0,
    'maximum_amount': None,
    'sort_order': 1,
    'status': 1,
    'bank_info': {
        'bank_name': 'BCA',
        'bank_code': '014',
        'account_name': 'PT ROYAL CORP',
    },
    'cara_bayar': [
        'Buka aplikasi Mobile Banking BCA atau kunjungi ATM BCA terdekat.',
        'Pilih menu Transfer / Pembayaran > Virtual Account (BCA Virtual Account).',
        'Masukkan nomor Virtual Account tujuan pembayaran yang tertera.',
        'Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.',
        'Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.',
        'Simpan bukti pembayaran atau struk transfer sebagai bukti sah.'
    ],
    'created_at': '2026-07-09T13:00:00',
    'updated_at': '2026-07-09T13:00:00'
}

@router.get('/', response_model=PaginatedListResponse[PaymentMethodRead], summary='List Payment Methods', description='Get a list of payment methods with bank info, instructions (cara bayar), and type details.', responses={200: {'description': 'A paginated list of payment methods', 'content': {'application/json': {'example': {'data': [PAYMENT_METHOD_EXAMPLE], 'total_count': 1, 'has_more': False, 'page': 1, 'items_per_page': 10}}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}})
async def list_payment_methods(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('payment-methods:read'))], payment_method_service: PaymentMethodServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await payment_method_service.get_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/{method_id}', response_model=PaymentMethodRead, summary='Get Payment Method', description='Get a single payment method by ID with bank info, instructions (cara bayar), and type details.', responses={200: {'description': 'The requested payment method', 'content': {'application/json': {'example': PAYMENT_METHOD_EXAMPLE}}}, 401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Not authenticated', 'support_id': 'a1b2c3d4'}}}}, 403: {'description': 'Not authorized', 'content': {'application/json': {'example': {'detail': 'Not authorized', 'support_id': 'a1b2c3d4'}}}}, 404: {'description': 'Payment method not found', 'content': {'application/json': {'example': {'detail': 'Payment method not found', 'support_id': 'a1b2c3d4'}}}}})
async def get_payment_method(method_id: UUID, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('payment-methods:read'))], payment_method_service: PaymentMethodServiceDep) -> dict[str, Any]:
    return await payment_method_service.get_by_id(db, method_id)