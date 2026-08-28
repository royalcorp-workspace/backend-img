from typing import Annotated, Any
from uuid import UUID
from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import StoreServiceDep
from .schemas import StoreChannelCreate, StoreChannelGroupCreate, StoreChannelGroupRead, StoreChannelGroupUpdate, StoreChannelRead, StoreChannelUpdate, StoreCreate, StoreGroupCreate, StoreGroupRead, StoreGroupUpdate, StoreRead, StoreTierCreate, StoreTierRead, StoreTierUpdate, StoreUpdate
router = APIRouter()
GROUP_EXAMPLE_NESTED = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'code': 'G001', 'name': 'Java Region Stores', 'description': 'Stores located in Java', 'status': True, 'sort_order': 1}
TIER_EXAMPLE_NESTED = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'code': 'GOLD_TIER', 'name': 'Gold Tier Dealer', 'description': 'High volume premium stores', 'level': 3, 'credit_limit': 500000000.0, 'status': True, 'sort_order': 1}
CHANNEL_GROUP_EXAMPLE_NESTED = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'code': 'ONLINE_CH', 'name': 'Online Sales Channels', 'description': 'Marketplaces and Webstore Group', 'status': True, 'sort_order': 1}
STORE_EXAMPLE_NESTED = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'store_group_id': 1, 'tier_id': 1, 'code': 'STR001', 'name': 'Royal Mattress Center Jakarta', 'owner_user_id': 1, 'credit_limit': 500000000.0, 'outstanding_balance': 15000000.0, 'address': 'Jl. Hayam Wuruk No. 12, Jakarta', 'phone': '021-1234567', 'email': 'jakarta@royalmattress.com', 'documents': ['https://example.com/siup.pdf'], 'payment_term': 30, 'status': True, 'sort_order': 1}
CHANNEL_EXAMPLE_NESTED = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'store_id': 1, 'store_channel_group_id': 1, 'code': 'TOKOPEDIA_OFFICIAL', 'name': 'Tokopedia Official Store', 'description': 'Direct online channel via Tokopedia', 'status': True, 'sort_order': 1}
GROUP_EXAMPLE = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'code': 'G001', 'name': 'Java Region Stores', 'description': 'Stores located in Java', 'status': True, 'sort_order': 1, 'created_at': '2026-07-09T13:00:00', 'updated_at': '2026-07-09T13:00:00', 'stores': [STORE_EXAMPLE_NESTED]}
TIER_EXAMPLE = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'code': 'GOLD_TIER', 'name': 'Gold Tier Dealer', 'description': 'High volume premium stores', 'level': 3, 'credit_limit': 500000000.0, 'status': True, 'sort_order': 1, 'created_at': '2026-07-09T13:00:00', 'updated_at': '2026-07-09T13:00:00', 'stores': [STORE_EXAMPLE_NESTED]}
CHANNEL_GROUP_EXAMPLE = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'code': 'ONLINE_CH', 'name': 'Online Sales Channels', 'description': 'Marketplaces and Webstore Group', 'status': True, 'sort_order': 1, 'created_at': '2026-07-09T13:00:00', 'updated_at': '2026-07-09T13:00:00', 'channels': [CHANNEL_EXAMPLE_NESTED]}
STORE_EXAMPLE = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'store_group_id': 1, 'tier_id': 1, 'code': 'STR001', 'name': 'Royal Mattress Center Jakarta', 'owner_user_id': 1, 'credit_limit': 500000000.0, 'outstanding_balance': 15000000.0, 'address': 'Jl. Hayam Wuruk No. 12, Jakarta', 'phone': '021-1234567', 'email': 'jakarta@royalmattress.com', 'documents': ['https://example.com/siup.pdf'], 'payment_term': 30, 'status': True, 'sort_order': 1, 'created_at': '2026-07-09T13:00:00', 'updated_at': '2026-07-09T13:00:00', 'group': GROUP_EXAMPLE_NESTED, 'tier': TIER_EXAMPLE_NESTED, 'channels': [CHANNEL_EXAMPLE_NESTED]}
CHANNEL_EXAMPLE = {'id': 'c1a3b2c3-d4e5-f6g7-h8i9-j0k1l2m3n4o5', 'store_id': 1, 'store_channel_group_id': 1, 'code': 'TOKOPEDIA_OFFICIAL', 'name': 'Tokopedia Official Store', 'description': 'Direct online channel via Tokopedia', 'status': True, 'sort_order': 1, 'created_at': '2026-07-09T13:00:00', 'updated_at': '2026-07-09T13:00:00', 'store': STORE_EXAMPLE_NESTED, 'channel_group': CHANNEL_GROUP_EXAMPLE_NESTED}

@router.get('/groups', response_model=PaginatedListResponse[StoreGroupRead], summary='List Store Groups', tags=['Store Groups'], responses={200: {'content': {'application/json': {'example': {'data': [GROUP_EXAMPLE], 'total_count': 1, 'has_more': False, 'page': 1, 'items_per_page': 10}}}}})
async def list_store_groups(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('stores:read'))], store_service: StoreServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await store_service.get_groups_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/tiers', response_model=PaginatedListResponse[StoreTierRead], summary='List Store Tiers', tags=['Store Tiers'], responses={200: {'content': {'application/json': {'example': {'data': [TIER_EXAMPLE], 'total_count': 1, 'has_more': False, 'page': 1, 'items_per_page': 10}}}}})
async def list_store_tiers(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('stores:read'))], store_service: StoreServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await store_service.get_tiers_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/channel-groups', response_model=PaginatedListResponse[StoreChannelGroupRead], summary='List Store Channel Groups', tags=['Store Channel Groups'], responses={200: {'content': {'application/json': {'example': {'data': [CHANNEL_GROUP_EXAMPLE], 'total_count': 1, 'has_more': False, 'page': 1, 'items_per_page': 10}}}}})
async def list_store_channel_groups(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('stores:read'))], store_service: StoreServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await store_service.get_channel_groups_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/', response_model=PaginatedListResponse[StoreRead], summary='List Stores', tags=['Stores'], responses={200: {'content': {'application/json': {'example': {'data': [STORE_EXAMPLE], 'total_count': 1, 'has_more': False, 'page': 1, 'items_per_page': 10}}}}})
async def list_stores(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('stores:read'))], store_service: StoreServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await store_service.get_stores_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/{store_id}', response_model=StoreRead, summary='Get Store', tags=['Stores'], responses={200: {'content': {'application/json': {'example': STORE_EXAMPLE}}}})
async def get_store(store_id: UUID, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('stores:read'))], store_service: StoreServiceDep) -> dict[str, Any]:
    return await store_service.get_store_by_id(db, store_id)

@router.get('/channels', response_model=PaginatedListResponse[StoreChannelRead], summary='List Store Channels', tags=['Store Channels'], responses={200: {'content': {'application/json': {'example': {'data': [CHANNEL_EXAMPLE], 'total_count': 1, 'has_more': False, 'page': 1, 'items_per_page': 10}}}}})
async def list_store_channels(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('stores:read'))], store_service: StoreServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await store_service.get_channels_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/channels/{channel_id}', response_model=StoreChannelRead, summary='Get Store Channel', tags=['Store Channels'], responses={200: {'content': {'application/json': {'example': CHANNEL_EXAMPLE}}}})
async def get_store_channel(channel_id: UUID, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('stores:read'))], store_service: StoreServiceDep) -> dict[str, Any]:
    return await store_service.get_channel_by_id(db, channel_id)