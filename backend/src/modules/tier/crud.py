from fastcrud import FastCRUD

from .models import Tier

crud_tiers: FastCRUD = FastCRUD(Tier, is_deleted_column="is_deleted")
