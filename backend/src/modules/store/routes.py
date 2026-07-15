from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import StoreServiceDep
from .schemas import (
    StoreChannelCreate,
    StoreChannelGroupCreate,
    StoreChannelGroupRead,
    StoreChannelGroupUpdate,
    StoreChannelRead,
    StoreChannelUpdate,
    StoreCreate,
    StoreGroupCreate,
    StoreGroupRead,
    StoreGroupUpdate,
    StoreRead,
    StoreTierCreate,
    StoreTierRead,
    StoreTierUpdate,
    StoreUpdate,
)

router = APIRouter()

# --- Examples ---
GROUP_EXAMPLE_NESTED = {
    "id": 1,
    "code": "G001",
    "name": "Java Region Stores",
    "description": "Stores located in Java",
    "status": True,
    "sort_order": 1,
}

TIER_EXAMPLE_NESTED = {
    "id": 1,
    "code": "GOLD_TIER",
    "name": "Gold Tier Dealer",
    "description": "High volume premium stores",
    "level": 3,
    "credit_limit": 500000000.0,
    "status": True,
    "sort_order": 1,
}

CHANNEL_GROUP_EXAMPLE_NESTED = {
    "id": 1,
    "code": "ONLINE_CH",
    "name": "Online Sales Channels",
    "description": "Marketplaces and Webstore Group",
    "status": True,
    "sort_order": 1,
}

STORE_EXAMPLE_NESTED = {
    "id": 1,
    "store_group_id": 1,
    "tier_id": 1,
    "code": "STR001",
    "name": "Royal Mattress Center Jakarta",
    "owner_user_id": 1,
    "credit_limit": 500000000.0,
    "outstanding_balance": 15000000.0,
    "address": "Jl. Hayam Wuruk No. 12, Jakarta",
    "phone": "021-1234567",
    "email": "jakarta@royalmattress.com",
    "documents": ["https://example.com/siup.pdf"],
    "payment_term": 30,
    "status": True,
    "sort_order": 1,
}

CHANNEL_EXAMPLE_NESTED = {
    "id": 1,
    "store_id": 1,
    "store_channel_group_id": 1,
    "code": "TOKOPEDIA_OFFICIAL",
    "name": "Tokopedia Official Store",
    "description": "Direct online channel via Tokopedia",
    "status": True,
    "sort_order": 1,
}

GROUP_EXAMPLE = {
    "id": 1,
    "code": "G001",
    "name": "Java Region Stores",
    "description": "Stores located in Java",
    "status": True,
    "sort_order": 1,
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
    "stores": [STORE_EXAMPLE_NESTED],
}

TIER_EXAMPLE = {
    "id": 1,
    "code": "GOLD_TIER",
    "name": "Gold Tier Dealer",
    "description": "High volume premium stores",
    "level": 3,
    "credit_limit": 500000000.0,
    "status": True,
    "sort_order": 1,
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
    "stores": [STORE_EXAMPLE_NESTED],
}

CHANNEL_GROUP_EXAMPLE = {
    "id": 1,
    "code": "ONLINE_CH",
    "name": "Online Sales Channels",
    "description": "Marketplaces and Webstore Group",
    "status": True,
    "sort_order": 1,
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
    "channels": [CHANNEL_EXAMPLE_NESTED],
}

STORE_EXAMPLE = {
    "id": 1,
    "store_group_id": 1,
    "tier_id": 1,
    "code": "STR001",
    "name": "Royal Mattress Center Jakarta",
    "owner_user_id": 1,
    "credit_limit": 500000000.0,
    "outstanding_balance": 15000000.0,
    "address": "Jl. Hayam Wuruk No. 12, Jakarta",
    "phone": "021-1234567",
    "email": "jakarta@royalmattress.com",
    "documents": ["https://example.com/siup.pdf"],
    "payment_term": 30,
    "status": True,
    "sort_order": 1,
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
    "group": GROUP_EXAMPLE_NESTED,
    "tier": TIER_EXAMPLE_NESTED,
    "channels": [CHANNEL_EXAMPLE_NESTED],
}

CHANNEL_EXAMPLE = {
    "id": 1,
    "store_id": 1,
    "store_channel_group_id": 1,
    "code": "TOKOPEDIA_OFFICIAL",
    "name": "Tokopedia Official Store",
    "description": "Direct online channel via Tokopedia",
    "status": True,
    "sort_order": 1,
    "created_at": "2026-07-09T13:00:00",
    "updated_at": "2026-07-09T13:00:00",
    "store": STORE_EXAMPLE_NESTED,
    "channel_group": CHANNEL_GROUP_EXAMPLE_NESTED,
}


# ==========================================
# 1. STORE GROUPS
# ==========================================
@router.get(
    "/groups",
    response_model=PaginatedListResponse[StoreGroupRead],
    summary="List Store Groups",
    tags=["Store Groups"],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "data": [GROUP_EXAMPLE],
                        "total_count": 1,
                        "has_more": False,
                        "page": 1,
                        "items_per_page": 10,
                    }
                }
            }
        }
    },
)
async def list_store_groups(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:read"))],
    store_service: StoreServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await store_service.get_groups_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.post(
    "/groups",
    response_model=StoreGroupRead,
    status_code=201,
    summary="Create Store Group",
    tags=["Store Groups"],
    responses={201: {"content": {"application/json": {"example": GROUP_EXAMPLE}}}},
)
async def create_store_group(
    group_in: StoreGroupCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:create"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.create_group(db, group_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/groups/{group_id}",
    response_model=StoreGroupRead,
    summary="Update Store Group",
    tags=["Store Groups"],
    responses={200: {"content": {"application/json": {"example": GROUP_EXAMPLE}}}},
)
async def update_store_group(
    group_id: UUID,
    group_in: StoreGroupUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:update"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.update_group(db, group_id, group_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/groups/{group_id}",
    status_code=204,
    summary="Delete Store Group",
    tags=["Store Groups"],
)
async def delete_store_group(
    group_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:delete"))],
    store_service: StoreServiceDep,
) -> None:
    await store_service.delete_group(db, group_id)


# ==========================================
# 2. STORE TIERS
# ==========================================
@router.get(
    "/tiers",
    response_model=PaginatedListResponse[StoreTierRead],
    summary="List Store Tiers",
    tags=["Store Tiers"],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "data": [TIER_EXAMPLE],
                        "total_count": 1,
                        "has_more": False,
                        "page": 1,
                        "items_per_page": 10,
                    }
                }
            }
        }
    },
)
async def list_store_tiers(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:read"))],
    store_service: StoreServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await store_service.get_tiers_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.post(
    "/tiers",
    response_model=StoreTierRead,
    status_code=201,
    summary="Create Store Tier",
    tags=["Store Tiers"],
    responses={201: {"content": {"application/json": {"example": TIER_EXAMPLE}}}},
)
async def create_store_tier(
    tier_in: StoreTierCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:create"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.create_tier(db, tier_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/tiers/{tier_id}",
    response_model=StoreTierRead,
    summary="Update Store Tier",
    tags=["Store Tiers"],
    responses={200: {"content": {"application/json": {"example": TIER_EXAMPLE}}}},
)
async def update_store_tier(
    tier_id: UUID,
    tier_in: StoreTierUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:update"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.update_tier(db, tier_id, tier_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/tiers/{tier_id}",
    status_code=204,
    summary="Delete Store Tier",
    tags=["Store Tiers"],
)
async def delete_store_tier(
    tier_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:delete"))],
    store_service: StoreServiceDep,
) -> None:
    await store_service.delete_tier(db, tier_id)


# ==========================================
# 3. STORE CHANNEL GROUPS
# ==========================================
@router.get(
    "/channel-groups",
    response_model=PaginatedListResponse[StoreChannelGroupRead],
    summary="List Store Channel Groups",
    tags=["Store Channel Groups"],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "data": [CHANNEL_GROUP_EXAMPLE],
                        "total_count": 1,
                        "has_more": False,
                        "page": 1,
                        "items_per_page": 10,
                    }
                }
            }
        }
    },
)
async def list_store_channel_groups(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:read"))],
    store_service: StoreServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await store_service.get_channel_groups_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.post(
    "/channel-groups",
    response_model=StoreChannelGroupRead,
    status_code=201,
    summary="Create Store Channel Group",
    tags=["Store Channel Groups"],
    responses={201: {"content": {"application/json": {"example": CHANNEL_GROUP_EXAMPLE}}}},
)
async def create_store_channel_group(
    channel_group_in: StoreChannelGroupCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:create"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.create_channel_group(db, channel_group_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/channel-groups/{channel_group_id}",
    response_model=StoreChannelGroupRead,
    summary="Update Store Channel Group",
    tags=["Store Channel Groups"],
    responses={200: {"content": {"application/json": {"example": CHANNEL_GROUP_EXAMPLE}}}},
)
async def update_store_channel_group(
    channel_group_id: UUID,
    channel_group_in: StoreChannelGroupUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:update"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.update_channel_group(db, channel_group_id, channel_group_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/channel-groups/{channel_group_id}",
    status_code=204,
    summary="Delete Store Channel Group",
    tags=["Store Channel Groups"],
)
async def delete_store_channel_group(
    channel_group_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:delete"))],
    store_service: StoreServiceDep,
) -> None:
    await store_service.delete_channel_group(db, channel_group_id)


# ==========================================
# 4. STORES
# ==========================================
@router.get(
    "/",
    response_model=PaginatedListResponse[StoreRead],
    summary="List Stores",
    tags=["Stores"],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "data": [STORE_EXAMPLE],
                        "total_count": 1,
                        "has_more": False,
                        "page": 1,
                        "items_per_page": 10,
                    }
                }
            }
        }
    },
)
async def list_stores(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:read"))],
    store_service: StoreServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await store_service.get_stores_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/{store_id}",
    response_model=StoreRead,
    summary="Get Store",
    tags=["Stores"],
    responses={200: {"content": {"application/json": {"example": STORE_EXAMPLE}}}},
)
async def get_store(
    store_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:read"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    return await store_service.get_store_by_id(db, store_id)


@router.post(
    "/",
    response_model=StoreRead,
    status_code=201,
    summary="Create Store",
    tags=["Stores"],
    responses={201: {"content": {"application/json": {"example": STORE_EXAMPLE}}}},
)
async def create_store(
    store_in: StoreCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:create"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.create_store(db, store_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/{store_id}",
    response_model=StoreRead,
    summary="Update Store",
    tags=["Stores"],
    responses={200: {"content": {"application/json": {"example": STORE_EXAMPLE}}}},
)
async def update_store(
    store_id: UUID,
    store_in: StoreUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:update"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.update_store(db, store_id, store_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/{store_id}",
    status_code=204,
    summary="Delete Store",
    tags=["Stores"],
)
async def delete_store(
    store_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:delete"))],
    store_service: StoreServiceDep,
) -> None:
    await store_service.delete_store(db, store_id)


# ==========================================
# 5. STORE CHANNELS
# ==========================================
@router.get(
    "/channels",
    response_model=PaginatedListResponse[StoreChannelRead],
    summary="List Store Channels",
    tags=["Store Channels"],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "data": [CHANNEL_EXAMPLE],
                        "total_count": 1,
                        "has_more": False,
                        "page": 1,
                        "items_per_page": 10,
                    }
                }
            }
        }
    },
)
async def list_store_channels(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:read"))],
    store_service: StoreServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await store_service.get_channels_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/channels/{channel_id}",
    response_model=StoreChannelRead,
    summary="Get Store Channel",
    tags=["Store Channels"],
    responses={200: {"content": {"application/json": {"example": CHANNEL_EXAMPLE}}}},
)
async def get_store_channel(
    channel_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:read"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    return await store_service.get_channel_by_id(db, channel_id)


@router.post(
    "/channels",
    response_model=StoreChannelRead,
    status_code=201,
    summary="Create Store Channel",
    tags=["Store Channels"],
    responses={201: {"content": {"application/json": {"example": CHANNEL_EXAMPLE}}}},
)
async def create_store_channel(
    channel_in: StoreChannelCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:create"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.create_channel(db, channel_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/channels/{channel_id}",
    response_model=StoreChannelRead,
    summary="Update Store Channel",
    tags=["Store Channels"],
    responses={200: {"content": {"application/json": {"example": CHANNEL_EXAMPLE}}}},
)
async def update_store_channel(
    channel_id: UUID,
    channel_in: StoreChannelUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:update"))],
    store_service: StoreServiceDep,
) -> dict[str, Any]:
    try:
        return await store_service.update_channel(db, channel_id, channel_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/channels/{channel_id}",
    status_code=204,
    summary="Delete Store Channel",
    tags=["Store Channels"],
)
async def delete_store_channel(
    channel_id: UUID,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("stores:delete"))],
    store_service: StoreServiceDep,
) -> None:
    await store_service.delete_channel(db, channel_id)
