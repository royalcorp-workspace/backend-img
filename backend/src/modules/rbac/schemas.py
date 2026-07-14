from typing import Annotated

from pydantic import BaseModel, Field

from ..common.schemas import TimestampSchema


class RoleBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    slug: Annotated[str, Field(min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")]
    description: Annotated[str | None, Field(max_length=255, default=None)]
    is_system: Annotated[bool, Field(default=False)]
    is_active: Annotated[bool, Field(default=True)]


class Role(RoleBase, TimestampSchema):
    id: int


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=255)
    is_system: bool | None = None
    is_active: bool | None = None


class PermissionBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    action: Annotated[str, Field(min_length=1, max_length=50)]
    subject: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str | None, Field(max_length=255, default=None)]
    is_active: Annotated[bool, Field(default=True)]


class Permission(PermissionBase, TimestampSchema):
    id: int


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    action: str | None = Field(default=None, min_length=1, max_length=50)
    subject: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class RoleWithPermissions(Role):
    permissions: list[Permission] = []


class PermissionWithRoles(Permission):
    roles: list[Role] = []
