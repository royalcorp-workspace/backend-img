from fastcrud import FastCRUD

from .models import Store, StoreChannel, StoreChannelGroup, StoreGroup, StoreTier

crud_store_groups: FastCRUD = FastCRUD(StoreGroup, is_deleted_column="deleted")
crud_store_tiers: FastCRUD = FastCRUD(StoreTier, is_deleted_column="deleted")
crud_store_channel_groups: FastCRUD = FastCRUD(StoreChannelGroup, is_deleted_column="deleted")
crud_stores: FastCRUD = FastCRUD(Store, is_deleted_column="deleted")
crud_store_channels: FastCRUD = FastCRUD(StoreChannel, is_deleted_column="deleted")
