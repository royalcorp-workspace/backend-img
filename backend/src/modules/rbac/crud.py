from fastcrud import FastCRUD

from .models import Permission, RBACRolePermission, RBACUserRole, Role

crud_roles: FastCRUD = FastCRUD(Role, is_deleted_column="deleted")
crud_permissions: FastCRUD = FastCRUD(Permission, is_deleted_column="deleted")
crud_user_roles: FastCRUD = FastCRUD(RBACUserRole, is_deleted_column="deleted")
crud_role_permissions: FastCRUD = FastCRUD(RBACRolePermission, is_deleted_column="deleted")
