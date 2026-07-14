from fastcrud import FastCRUD

from .models import Permission, RBACRolePermission, RBACUserRole, Role

crud_roles: FastCRUD = FastCRUD(Role)
crud_permissions: FastCRUD = FastCRUD(Permission)
crud_user_roles: FastCRUD = FastCRUD(RBACUserRole)
crud_role_permissions: FastCRUD = FastCRUD(RBACRolePermission)
