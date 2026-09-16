from typing import Any
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from ..common.utils import get_media_url
from ..product.models import Brand
from .crud import crud_categories
from .schemas import CategoryCreate, CategoryRead, CategoryUpdate

logger = get_logger()


def _brand_to_category_dict(brand: Brand) -> dict[str, Any]:
    logo_url = get_media_url(brand.logo)
    banner_url = get_media_url(brand.banner_web or brand.banner_mobile)
    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "parent_id": None,
        "description": brand.description,
        "image": logo_url,
        "logo": logo_url,
        "banner": banner_url,
        "banner_web": get_media_url(brand.banner_web),
        "banner_mobile": get_media_url(brand.banner_mobile),
        "tagline": None,
        "sort_order": brand.sort_order or 0,
        "status": bool(brand.status) if brand.status is not None else True,
        "courier_setting_type": "detail",
        "courier_type": "keduanya",
        "is_featured": bool(brand.is_featured),
    }


class CategoryService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        stmt = (
            select(Brand)
            .where(Brand.deleted == False, or_(Brand.status == 1, Brand.status.is_(None)))
        )
        count_stmt = select(func.count()).select_from(Brand).where(
            Brand.deleted == False, or_(Brand.status == 1, Brand.status.is_(None))
        )
        for key, value in filters.items():
            if "__" in key:
                field_name, operator = key.rsplit("__", 1)
                column = getattr(Brand, field_name, None)
                if column is not None:
                    if operator == "ilike":
                        stmt = stmt.where(column.ilike(value))
                        count_stmt = count_stmt.where(column.ilike(value))
                    elif operator == "like":
                        stmt = stmt.where(column.like(value))
                        count_stmt = count_stmt.where(column.like(value))
                    elif operator == "eq":
                        stmt = stmt.where(column == value)
                        count_stmt = count_stmt.where(column == value)
            elif hasattr(Brand, key):
                stmt = stmt.where(getattr(Brand, key) == value)
                count_stmt = count_stmt.where(getattr(Brand, key) == value)

        stmt = stmt.order_by(Brand.sort_order.asc(), Brand.name.asc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        brands = result.scalars().all()
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        return {
            "data": [_brand_to_category_dict(b) for b in brands],
            "total_count": total,
        }

    async def get_by_id(self, db: AsyncSession, category_id: Any) -> dict[str, Any]:
        stmt = select(Brand).where(Brand.id == category_id, Brand.deleted == False)
        result = await db.execute(stmt)
        brand = result.scalar_one_or_none()
        if brand:
            return _brand_to_category_dict(brand)

        category = await crud_categories.get(db=db, id=category_id, deleted=False)
        if not category:
            raise ResourceNotFoundError(f"Category or Brand with ID {category_id} not found")
        return category

    async def get_tree(self, db: AsyncSession) -> list[dict[str, Any]]:
        stmt = (
            select(Brand)
            .where(Brand.deleted == False, or_(Brand.status == 1, Brand.status.is_(None)))
            .order_by(Brand.sort_order.asc(), Brand.name.asc())
        )
        result = await db.execute(stmt)
        brands = result.scalars().all()
        return [{**_brand_to_category_dict(b), "children": []} for b in brands]

    async def get_flat(self, db: AsyncSession) -> list[dict[str, Any]]:
        stmt = (
            select(Brand)
            .where(Brand.deleted == False, or_(Brand.status == 1, Brand.status.is_(None)))
            .order_by(Brand.sort_order.asc(), Brand.name.asc())
        )
        result = await db.execute(stmt)
        brands = result.scalars().all()
        return [_brand_to_category_dict(b) for b in brands]

    async def create(self, db: AsyncSession, category_in: CategoryCreate) -> dict[str, Any]:
        existing = await crud_categories.get(db=db, slug=category_in.slug)
        if existing:
            raise ResourceExistsError(f"Category with slug '{category_in.slug}' already exists")
        return await crud_categories.create(db=db, object=category_in)

    async def update(self, db: AsyncSession, category_id: int, category_in: CategoryUpdate) -> dict[str, Any]:
        category = await crud_categories.get(db=db, id=category_id, deleted=False)
        if not category:
            raise ResourceNotFoundError(f"Category with ID {category_id} not found")
        if category_in.slug and category_in.slug != category.get("slug"):
            existing = await crud_categories.get(db=db, slug=category_in.slug)
            if existing:
                raise ResourceExistsError(f"Category with slug '{category_in.slug}' already exists")
        return await crud_categories.update(db=db, object=category_in, id=category_id)

    async def delete(self, db: AsyncSession, category_id: int) -> None:
        category = await crud_categories.get(db=db, id=category_id, deleted=False)
        if not category:
            raise ResourceNotFoundError(f"Category with ID {category_id} not found")
        await crud_categories.delete(db=db, id=category_id)


category_service = CategoryService()
