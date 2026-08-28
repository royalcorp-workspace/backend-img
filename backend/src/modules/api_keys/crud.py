from fastcrud import FastCRUD

from .models import APIKey, KeyPermission, KeyUsage

crud_api_keys: FastCRUD = FastCRUD(APIKey, is_deleted_column="deleted")
crud_key_usage: FastCRUD = FastCRUD(KeyUsage, is_deleted_column="deleted")
crud_key_permissions: FastCRUD = FastCRUD(KeyPermission, is_deleted_column="deleted")
