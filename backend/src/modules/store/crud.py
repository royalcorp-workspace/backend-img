from fastcrud import FastCRUD

from .models import Store, StoreChannel, StoreChannelGroup, StoreGroup, StoreTier

crud_store_groups: FastCRUD = FastCRUD(StoreGroup)
crud_store_tiers: FastCRUD = FastCRUD(StoreTier)
crud_store_channel_groups: FastCRUD = FastCRUD(StoreChannelGroup)
crud_stores: FastCRUD = FastCRUD(Store)
crud_store_channels: FastCRUD = FastCRUD(StoreChannel)
