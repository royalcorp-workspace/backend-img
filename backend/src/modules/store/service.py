from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import (
    crud_store_channel_groups,
    crud_store_channels,
    crud_store_groups,
    crud_store_tiers,
    crud_stores,
)
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

logger = get_logger()


class StoreService:
    # --- Store Group ---
    async def get_groups_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_store_groups.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=StoreGroupRead, **filters
        )

    async def get_group_by_id(self, db: AsyncSession, group_id: UUID) -> dict[str, Any]:
        res = await crud_store_groups.get(db=db, id=group_id, deleted=False)
        if not res:
            raise ResourceNotFoundError(f"Store Group with ID {group_id} not found")
        return res

    async def create_group(self, db: AsyncSession, group_in: StoreGroupCreate) -> dict[str, Any]:
        existing = await crud_store_groups.get(db=db, code=group_in.code)
        if existing:
            raise ResourceExistsError(f"Store Group with code '{group_in.code}' already exists")
        res = await crud_store_groups.create(db=db, object=group_in)
        await db.commit()
        return res

    async def update_group(self, db: AsyncSession, group_id: UUID, group_in: StoreGroupUpdate) -> dict[str, Any]:
        group = await crud_store_groups.get(db=db, id=group_id, deleted=False)
        if not group:
            raise ResourceNotFoundError(f"Store Group with ID {group_id} not found")
        if group_in.code and group_in.code != group.get("code"):
            existing = await crud_store_groups.get(db=db, code=group_in.code)
            if existing:
                raise ResourceExistsError(f"Store Group with code '{group_in.code}' already exists")
        res = await crud_store_groups.update(db=db, object=group_in, id=group_id)
        await db.commit()
        return res

    async def delete_group(self, db: AsyncSession, group_id: UUID) -> None:
        group = await crud_store_groups.get(db=db, id=group_id, deleted=False)
        if not group:
            raise ResourceNotFoundError(f"Store Group with ID {group_id} not found")
        await crud_store_groups.delete(db=db, id=group_id)
        await db.commit()

    # --- Store Tier ---
    async def get_tiers_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_store_tiers.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=StoreTierRead, **filters
        )

    async def get_tier_by_id(self, db: AsyncSession, tier_id: UUID) -> dict[str, Any]:
        res = await crud_store_tiers.get(db=db, id=tier_id, deleted=False)
        if not res:
            raise ResourceNotFoundError(f"Store Tier with ID {tier_id} not found")
        return res

    async def create_tier(self, db: AsyncSession, tier_in: StoreTierCreate) -> dict[str, Any]:
        existing = await crud_store_tiers.get(db=db, code=tier_in.code)
        if existing:
            raise ResourceExistsError(f"Store Tier with code '{tier_in.code}' already exists")
        res = await crud_store_tiers.create(db=db, object=tier_in)
        await db.commit()
        return res

    async def update_tier(self, db: AsyncSession, tier_id: UUID, tier_in: StoreTierUpdate) -> dict[str, Any]:
        tier = await crud_store_tiers.get(db=db, id=tier_id, deleted=False)
        if not tier:
            raise ResourceNotFoundError(f"Store Tier with ID {tier_id} not found")
        if tier_in.code and tier_in.code != tier.get("code"):
            existing = await crud_store_tiers.get(db=db, code=tier_in.code)
            if existing:
                raise ResourceExistsError(f"Store Tier with code '{tier_in.code}' already exists")
        res = await crud_store_tiers.update(db=db, object=tier_in, id=tier_id)
        await db.commit()
        return res

    async def delete_tier(self, db: AsyncSession, tier_id: UUID) -> None:
        tier = await crud_store_tiers.get(db=db, id=tier_id, deleted=False)
        if not tier:
            raise ResourceNotFoundError(f"Store Tier with ID {tier_id} not found")
        await crud_store_tiers.delete(db=db, id=tier_id)
        await db.commit()

    # --- Store Channel Group ---
    async def get_channel_groups_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_store_channel_groups.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=StoreChannelGroupRead, **filters
        )

    async def get_channel_group_by_id(self, db: AsyncSession, channel_group_id: UUID) -> dict[str, Any]:
        res = await crud_store_channel_groups.get(db=db, id=channel_group_id, deleted=False)
        if not res:
            raise ResourceNotFoundError(f"Store Channel Group with ID {channel_group_id} not found")
        return res

    async def create_channel_group(
        self, db: AsyncSession, channel_group_in: StoreChannelGroupCreate
    ) -> dict[str, Any]:
        existing = await crud_store_channel_groups.get(db=db, code=channel_group_in.code)
        if existing:
            raise ResourceExistsError(f"Store Channel Group with code '{channel_group_in.code}' already exists")
        res = await crud_store_channel_groups.create(db=db, object=channel_group_in)
        await db.commit()
        return res

    async def update_channel_group(
        self, db: AsyncSession, channel_group_id: UUID, channel_group_in: StoreChannelGroupUpdate
    ) -> dict[str, Any]:
        group = await crud_store_channel_groups.get(db=db, id=channel_group_id, deleted=False)
        if not group:
            raise ResourceNotFoundError(f"Store Channel Group with ID {channel_group_id} not found")
        if channel_group_in.code and channel_group_in.code != group.get("code"):
            existing = await crud_store_channel_groups.get(db=db, code=channel_group_in.code)
            if existing:
                raise ResourceExistsError(f"Store Channel Group with code '{channel_group_in.code}' already exists")
        res = await crud_store_channel_groups.update(db=db, object=channel_group_in, id=channel_group_id)
        await db.commit()
        return res

    async def delete_channel_group(self, db: AsyncSession, channel_group_id: UUID) -> None:
        group = await crud_store_channel_groups.get(db=db, id=channel_group_id, deleted=False)
        if not group:
            raise ResourceNotFoundError(f"Store Channel Group with ID {channel_group_id} not found")
        await crud_store_channel_groups.delete(db=db, id=channel_group_id)
        await db.commit()

    # --- Store ---
    async def get_stores_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_stores.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=StoreRead, **filters
        )

    async def get_store_by_id(self, db: AsyncSession, store_id: UUID) -> dict[str, Any]:
        res = await crud_stores.get(db=db, id=store_id, deleted=False)
        if not res:
            raise ResourceNotFoundError(f"Store with ID {store_id} not found")
        return res

    async def create_store(self, db: AsyncSession, store_in: StoreCreate) -> dict[str, Any]:
        # Validate StoreGroup & StoreTier exist
        group = await crud_store_groups.get(db=db, id=store_in.store_group_id, deleted=False)
        if not group:
            raise ResourceNotFoundError(f"Store Group with ID {store_in.store_group_id} not found")
        if store_in.tier_id:
            tier = await crud_store_tiers.get(db=db, id=store_in.tier_id, deleted=False)
            if not tier:
                raise ResourceNotFoundError(f"Store Tier with ID {store_in.tier_id} not found")

        existing = await crud_stores.get(db=db, code=store_in.code)
        if existing:
            raise ResourceExistsError(f"Store with code '{store_in.code}' already exists")
        res = await crud_stores.create(db=db, object=store_in)
        await db.commit()
        return res

    async def update_store(self, db: AsyncSession, store_id: UUID, store_in: StoreUpdate) -> dict[str, Any]:
        store = await crud_stores.get(db=db, id=store_id, deleted=False)
        if not store:
            raise ResourceNotFoundError(f"Store with ID {store_id} not found")

        if store_in.store_group_id:
            group = await crud_store_groups.get(db=db, id=store_in.store_group_id, deleted=False)
            if not group:
                raise ResourceNotFoundError(f"Store Group with ID {store_in.store_group_id} not found")
        if store_in.tier_id:
            tier = await crud_store_tiers.get(db=db, id=store_in.tier_id, deleted=False)
            if not tier:
                raise ResourceNotFoundError(f"Store Tier with ID {store_in.tier_id} not found")

        if store_in.code and store_in.code != store.get("code"):
            existing = await crud_stores.get(db=db, code=store_in.code)
            if existing:
                raise ResourceExistsError(f"Store with code '{store_in.code}' already exists")
        res = await crud_stores.update(db=db, object=store_in, id=store_id)
        await db.commit()
        return res

    async def delete_store(self, db: AsyncSession, store_id: UUID) -> None:
        store = await crud_stores.get(db=db, id=store_id, deleted=False)
        if not store:
            raise ResourceNotFoundError(f"Store with ID {store_id} not found")
        await crud_stores.delete(db=db, id=store_id)
        await db.commit()

    # --- Store Channel ---
    async def get_channels_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_store_channels.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=StoreChannelRead, **filters
        )

    async def get_channel_by_id(self, db: AsyncSession, channel_id: UUID) -> dict[str, Any]:
        res = await crud_store_channels.get(db=db, id=channel_id, deleted=False)
        if not res:
            raise ResourceNotFoundError(f"Store Channel with ID {channel_id} not found")
        return res

    async def create_channel(self, db: AsyncSession, channel_in: StoreChannelCreate) -> dict[str, Any]:
        # Validate Store & StoreChannelGroup exist
        store = await crud_stores.get(db=db, id=channel_in.store_id, deleted=False)
        if not store:
            raise ResourceNotFoundError(f"Store with ID {channel_in.store_id} not found")
        group = await crud_store_channel_groups.get(db=db, id=channel_in.store_channel_group_id, deleted=False)
        if not group:
            raise ResourceNotFoundError(f"Store Channel Group with ID {channel_in.store_channel_group_id} not found")

        existing = await crud_store_channels.get(db=db, code=channel_in.code)
        if existing:
            raise ResourceExistsError(f"Store Channel with code '{channel_in.code}' already exists")
        res = await crud_store_channels.create(db=db, object=channel_in)
        await db.commit()
        return res

    async def update_channel(self, db: AsyncSession, channel_id: UUID, channel_in: StoreChannelUpdate) -> dict[str, Any]:
        channel = await crud_store_channels.get(db=db, id=channel_id, deleted=False)
        if not channel:
            raise ResourceNotFoundError(f"Store Channel with ID {channel_id} not found")

        if channel_in.store_id:
            store = await crud_stores.get(db=db, id=channel_in.store_id, deleted=False)
            if not store:
                raise ResourceNotFoundError(f"Store with ID {channel_in.store_id} not found")
        if channel_in.store_channel_group_id:
            group = await crud_store_channel_groups.get(db=db, id=channel_in.store_channel_group_id, deleted=False)
            if not group:
                raise ResourceNotFoundError(f"Store Channel Group with ID {channel_in.store_channel_group_id} not found")

        if channel_in.code and channel_in.code != channel.get("code"):
            existing = await crud_store_channels.get(db=db, code=channel_in.code)
            if existing:
                raise ResourceExistsError(f"Store Channel with code '{channel_in.code}' already exists")
        res = await crud_store_channels.update(db=db, object=channel_in, id=channel_id)
        await db.commit()
        return res

    async def delete_channel(self, db: AsyncSession, channel_id: UUID) -> None:
        channel = await crud_store_channels.get(db=db, id=channel_id, deleted=False)
        if not channel:
            raise ResourceNotFoundError(f"Store Channel with ID {channel_id} not found")
        await crud_store_channels.delete(db=db, id=channel_id)
        await db.commit()


store_service = StoreService()
