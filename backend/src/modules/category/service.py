from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import crud_categories
from .schemas import CategoryCreate, CategoryRead, CategoryUpdate

logger = get_logger()


class CategoryService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_categories.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=CategoryRead, **filters
        )

    async def get_by_id(self, db: AsyncSession, category_id: int) -> dict[str, Any]:
        category = await crud_categories.get(db=db, id=category_id, is_deleted=False)
        if not category:
            raise ResourceNotFoundError(f"Category with ID {category_id} not found")
        return category

    async def get_tree(self, db: AsyncSession) -> list[dict[str, Any]]:
        result = await crud_categories.get_multi(db=db, schema_to_select=CategoryRead, is_deleted=False)
        categories = {c["id"]: c for c in result.get("data", [])}
        roots = []
        for cat in categories.values():
            cat.setdefault("children", [])
            if cat.get("parent_id") in (None, 0, cat["id"]):
                roots.append(cat)
            else:
                parent = categories.get(cat.get("parent_id"))
                if parent:
                    parent.setdefault("children", []).append(cat)
        return roots

    async def get_flat(self, db: AsyncSession) -> list[dict[str, Any]]:
        result = await crud_categories.get_multi(db=db, schema_to_select=CategoryRead, is_deleted=False)
        return result.get("data", [])

    async def create(self, db: AsyncSession, category_in: CategoryCreate) -> dict[str, Any]:
        existing = await crud_categories.get(db=db, slug=category_in.slug)
        if existing:
            raise ResourceExistsError(f"Category with slug '{category_in.slug}' already exists")
        return await crud_categories.create(db=db, object=category_in)

    async def update(self, db: AsyncSession, category_id: int, category_in: CategoryUpdate) -> dict[str, Any]:
        category = await crud_categories.get(db=db, id=category_id, is_deleted=False)
        if not category:
            raise ResourceNotFoundError(f"Category with ID {category_id} not found")
        if category_in.slug and category_in.slug != category.get("slug"):
            existing = await crud_categories.get(db=db, slug=category_in.slug)
            if existing:
                raise ResourceExistsError(f"Category with slug '{category_in.slug}' already exists")
        return await crud_categories.update(db=db, object=category_in, id=category_id)

    async def delete(self, db: AsyncSession, category_id: int) -> None:
        category = await crud_categories.get(db=db, id=category_id, is_deleted=False)
        if not category:
            raise ResourceNotFoundError(f"Category with ID {category_id} not found")
        await crud_categories.delete(db=db, id=category_id)


category_service = CategoryService()
