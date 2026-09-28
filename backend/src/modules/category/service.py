from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import crud_categories
from .schemas import CategoryCreate, CategoryRead, CategoryUpdate

logger = get_logger()


class CategoryService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        sort_columns = filters.pop("sort_columns", ["sort_order", "name"])
        sort_orders = filters.pop("sort_orders", ["asc", "asc"])
        return await crud_categories.get_multi(
            db=db,
            offset=skip,
            limit=limit,
            schema_to_select=CategoryRead,
            sort_columns=sort_columns,
            sort_orders=sort_orders,
            deleted=False,
            **filters,
        )

    async def get_by_id(self, db: AsyncSession, category_id: uuid.UUID | Any) -> dict[str, Any]:
        if isinstance(category_id, str):
            try:
                category_id = uuid.UUID(category_id)
            except ValueError:
                category = await crud_categories.get(db=db, slug=category_id, deleted=False)
                if not category:
                    raise ResourceNotFoundError(f"Category with slug '{category_id}' not found")
                return category

        category = await crud_categories.get(db=db, id=category_id, deleted=False)
        if not category:
            raise ResourceNotFoundError(f"Category with ID {category_id} not found")
        return category

    async def get_tree(self, db: AsyncSession) -> list[dict[str, Any]]:
        result = await crud_categories.get_multi(
            db=db,
            schema_to_select=CategoryRead,
            deleted=False,
            sort_columns=["sort_order", "name"],
            sort_orders=["asc", "asc"],
            limit=None,
        )
        categories = {c["id"]: dict(c) for c in result.get("data", [])}
        roots = []
        for cat in categories.values():
            cat.setdefault("children", [])
            parent_id = cat.get("parent_id")
            if parent_id in (None, 0, cat["id"]):
                roots.append(cat)
            else:
                parent = categories.get(parent_id)
                if parent:
                    parent.setdefault("children", []).append(cat)
                else:
                    roots.append(cat)
        return roots

    async def get_flat(self, db: AsyncSession) -> list[dict[str, Any]]:
        result = await crud_categories.get_multi(
            db=db,
            schema_to_select=CategoryRead,
            deleted=False,
            sort_columns=["sort_order", "name"],
            sort_orders=["asc", "asc"],
            limit=None,
        )
        return result.get("data", [])

    async def create(self, db: AsyncSession, category_in: CategoryCreate) -> dict[str, Any]:
        existing = await crud_categories.get(db=db, slug=category_in.slug)
        if existing:
            raise ResourceExistsError(f"Category with slug '{category_in.slug}' already exists")
        return await crud_categories.create(db=db, object=category_in)

    async def update(self, db: AsyncSession, category_id: uuid.UUID | Any, category_in: CategoryUpdate) -> dict[str, Any]:
        category = await crud_categories.get(db=db, id=category_id, deleted=False)
        if not category:
            raise ResourceNotFoundError(f"Category with ID {category_id} not found")
        if category_in.slug and category_in.slug != category.get("slug"):
            existing = await crud_categories.get(db=db, slug=category_in.slug)
            if existing:
                raise ResourceExistsError(f"Category with slug '{category_in.slug}' already exists")
        return await crud_categories.update(db=db, object=category_in, id=category_id)

    async def delete(self, db: AsyncSession, category_id: uuid.UUID | Any) -> None:
        category = await crud_categories.get(db=db, id=category_id, deleted=False)
        if not category:
            raise ResourceNotFoundError(f"Category with ID {category_id} not found")
        await crud_categories.delete(db=db, id=category_id)


category_service = CategoryService()
