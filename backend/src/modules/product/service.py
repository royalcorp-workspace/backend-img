from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import (
    crud_colors,
    crud_images,
    crud_products,
    crud_variants,
)
from .models import PriceProductSetting, PriceProductSettingItem, Product, ProductVariant
from .schemas import (
    ProductColorCreate,
    ProductCreate,
    ProductImageCreate,
    ProductUpdate,
    ProductVariantCreate,
)

logger = get_logger()


def _product_to_dict(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "category_id": product.category_id,
        "thumbnail": product.thumbnail,
        "alt_text": product.alt_text,
        "short_description": product.short_description,
        "description": product.description,
        "base_price": product.base_price,
        "segments": product.segments,
        "best_seller": product.best_seller,
        "is_new": product.is_new,
        "sort_order": product.sort_order,
        "status": product.status,
        "creator": product.creator,
        "editor": product.editor,
        "deleted": product.deleted,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "images": [
            {
                "id": img.id,
                "product_id": img.product_id,
                "image": img.image,
                "alt_text": img.alt_text,
                "sort_order": img.sort_order,
                "status": img.status,
                "created_at": img.created_at,
                "updated_at": img.updated_at,
                "deleted": img.deleted,
            }
            for img in (product.images or [])
        ],
        "variants": [
            {
                "id": v.id,
                "product_id": v.product_id,
                "sku": v.sku,
                "variant_name": v.variant_name,
                "price": v.price,
                "stock_qty": v.stock_qty,
                "attributes": v.attributes,
                "creator": v.creator,
                "editor": v.editor,
                "deleted": v.deleted,
                "created_at": v.created_at,
                "updated_at": v.updated_at,
                "price_product_settings": [],
                "final_price": 0.0,
            }
            for v in (product.variants or [])
        ],
        "colors": [
            {
                "id": c.id,
                "product_id": c.product_id,
                "color_name": c.color_name,
                "color_code": c.color_code,
                "status": c.status,
                "creator": c.creator,
                "editor": c.editor,
                "deleted": c.deleted,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in (product.colors or [])
        ],
        "price_product_settings": [],
        "final_price": 0.0,
        "reviews": [
            {
                "id": r.id,
                "product_id": r.product_id,
                "order_id": r.order_id,
                "user_name": r.user_name,
                "user_email": r.user_email,
                "rating": r.rating,
                "text": r.text,
                "image_url": r.image_url,
                "is_approved": r.is_approved,
                "is_published": r.is_published,
                "report_count": r.report_count,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "deleted": r.deleted,
            }
            for r in (product.reviews or [])
        ],
    }


def _variant_to_dict(variant: ProductVariant) -> dict[str, Any]:
    return {
        "id": variant.id,
        "product_id": variant.product_id,
        "sku": variant.sku,
        "variant_name": variant.variant_name,
        "price": variant.price,
        "stock_qty": variant.stock_qty,
        "attributes": variant.attributes,
        "creator": variant.creator,
        "editor": variant.editor,
        "deleted": variant.deleted,
        "created_at": variant.created_at,
        "updated_at": variant.updated_at,
        "price_product_settings": [],
        "final_price": 0.0,
    }


def _price_setting_item_to_dict(item: PriceProductSettingItem) -> dict[str, Any]:
    pps = item.setting
    return {
        "id": pps.id,
        "code": pps.code,
        "title": pps.title,
        "description": pps.description,
        "type": pps.type,
        "scope": pps.scope,
        "discount_type": item.discount_type,
        "discount_value": item.discount_value,
        "min_purchase": pps.min_purchase,
        "max_discount": pps.max_discount,
        "start_date": pps.start_date.isoformat() if pps.start_date else None,
        "end_date": pps.end_date.isoformat() if pps.end_date else None,
        "image_url": pps.image_url,
        "is_active": pps.is_active,
        "is_featured": pps.is_featured,
        "sort_order": pps.sort_order,
        "volume_tiers": [
            {
                "id": vt.id,
                "min_purchase": vt.min_purchase,
                "discount_type": vt.discount_type,
                "discount_value": vt.discount_value,
                "sort_order": vt.sort_order,
            }
            for vt in (pps.volume_tiers or [])
        ],
    }


def _calculate_final_price(original_price: float, price_settings: list[dict[str, Any]]) -> float:
    if not price_settings:
        return original_price
    pps = price_settings[0]
    if not pps.get("is_active"):
        return original_price
    discount_type = pps.get("discount_type")
    discount_value = pps.get("discount_value")
    if discount_type is None or discount_value is None:
        return original_price
    if discount_type == 1:
        return round(original_price * (1 - discount_value / 100), 2)
    if discount_type == 2:
        return round(max(0, original_price - discount_value), 2)
    return original_price


class ProductService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        query = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.colors),
                selectinload(Product.reviews),
            )
            .where(Product.deleted.is_(False))
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(Product).where(Product.deleted.is_(False))

        for key, value in filters.items():
            if "__" in key:
                field_name, operator = key.rsplit("__", 1)
                column = getattr(Product, field_name, None)
                if column is not None:
                    if operator == "ilike":
                        query = query.where(column.ilike(value))
                        count_query = count_query.where(column.ilike(value))
                    elif operator == "like":
                        query = query.where(column.like(value))
                        count_query = count_query.where(column.like(value))
                    elif operator == "eq":
                        query = query.where(column == value)
                        count_query = count_query.where(column == value)
                    elif operator == "gt":
                        query = query.where(column > value)
                        count_query = count_query.where(column > value)
                    elif operator == "lt":
                        query = query.where(column < value)
                        count_query = count_query.where(column < value)
                    elif operator == "gte":
                        query = query.where(column >= value)
                        count_query = count_query.where(column >= value)
                    elif operator == "lte":
                        query = query.where(column <= value)
                        count_query = count_query.where(column <= value)
                    elif operator == "ne":
                        query = query.where(column != value)
                        count_query = count_query.where(column != value)
                    elif operator == "in":
                        query = query.where(column.in_(value))
                        count_query = count_query.where(column.in_(value))
            elif hasattr(Product, key):
                query = query.where(getattr(Product, key) == value)
                count_query = count_query.where(getattr(Product, key) == value)

        result = await db.execute(query)
        products = result.scalars().all()
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        if products:
            product_ids = [p.id for p in products]
            items_stmt = (
                select(PriceProductSettingItem)
                .options(selectinload(PriceProductSettingItem.setting).selectinload(PriceProductSetting.volume_tiers))
                .where(PriceProductSettingItem.product_id.in_(product_ids), PriceProductSettingItem.deleted.is_(False))
            )
            items_result = await db.execute(items_stmt)
            items = items_result.scalars().all()

            items_by_product_variant: dict[UUID, dict[UUID | None, list[PriceProductSettingItem]]] = {}
            for item in items:
                pid = item.product_id
                vid = item.variant_id
                items_by_product_variant.setdefault(pid, {}).setdefault(vid, []).append(item)

        product_dicts = []
        for product in products:
            product_dict = _product_to_dict(product)
            product_settings = [
                _price_setting_item_to_dict(item)
                for item in (items_by_product_variant.get(product.id, {}).get(None) or [])
            ]
            product_dict["price_product_settings"] = product_settings
            product_dict["final_price"] = _calculate_final_price(
                float(product.base_price or 0),
                product_settings,
            )

            variant_map = {v.id: v for v in (product.variants or [])}
            for variant in product_dict.get("variants", []):
                variant_id = variant["id"]
                v = variant_map.get(variant_id)
                if v:
                    variant_specific = [
                        _price_setting_item_to_dict(item)
                        for item in (items_by_product_variant.get(product.id, {}).get(variant_id) or [])
                    ]
                    if variant_specific:
                        variant["price_product_settings"] = variant_specific
                    else:
                        variant["price_product_settings"] = product_settings
                    variant["final_price"] = _calculate_final_price(
                        float(v.price or 0),
                        variant["price_product_settings"],
                    )

            reviews = product_dict.get("reviews", [])
            avg_rating = (
                sum(r["rating"] for r in reviews if r.get("rating")) / len(reviews) if reviews else 0
            )
            product_dict["avg_rating"] = round(avg_rating, 2)
            product_dict["total_reviews"] = len(reviews)
            product_dicts.append(product_dict)

        return {
            "data": product_dicts,
            "total_count": total,
            "has_more": (skip + len(products)) < total,
        }

    async def get_by_id(self, db: AsyncSession, product_id: UUID) -> dict[str, Any]:
        stmt = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.colors),
                selectinload(Product.reviews),
            )
            .where(Product.id == product_id, Product.deleted.is_(False))
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            raise ResourceNotFoundError(f"Product with ID {product_id} not found")

        items_stmt = (
            select(PriceProductSettingItem)
            .options(selectinload(PriceProductSettingItem.setting).selectinload(PriceProductSetting.volume_tiers))
            .where(PriceProductSettingItem.product_id == product_id, PriceProductSettingItem.deleted.is_(False))
        )
        items_result = await db.execute(items_stmt)
        items = items_result.scalars().all()

        items_by_variant: dict[UUID | None, list[PriceProductSettingItem]] = {}
        for item in items:
            items_by_variant.setdefault(item.variant_id, []).append(item)

        product_dict = _product_to_dict(product)
        product_dict["price_product_settings"] = [
            _price_setting_item_to_dict(item)
            for item in (items_by_variant.get(None) or [])
        ]
        product_dict["final_price"] = _calculate_final_price(
            float(product.base_price or 0),
            product_dict["price_product_settings"],
        )

        variant_map = {v.id: v for v in (product.variants or [])}
        for variant in product_dict.get("variants", []):
            variant_id = variant["id"]
            v = variant_map.get(variant_id)
            if v:
                variant_specific = [
                    _price_setting_item_to_dict(item)
                    for item in (items_by_variant.get(variant_id) or [])
                ]
                if variant_specific:
                    variant["price_product_settings"] = variant_specific
                else:
                    variant["price_product_settings"] = product_dict["price_product_settings"]
                variant["final_price"] = _calculate_final_price(
                    float(v.price or 0),
                    variant["price_product_settings"],
                )

        reviews = product_dict.get("reviews", [])
        avg_rating = (
            sum(r["rating"] for r in reviews if r.get("rating")) / len(reviews) if reviews else 0
        )
        product_dict["avg_rating"] = round(avg_rating, 2)
        product_dict["total_reviews"] = len(reviews)
        return product_dict

    async def create(self, db: AsyncSession, product_in: ProductCreate) -> dict[str, Any]:
        existing = await crud_products.get(db=db, slug=product_in.slug)
        if existing:
            raise ResourceExistsError(f"Product with slug '{product_in.slug}' already exists")
        return await crud_products.create(db=db, object=product_in)

    async def update(self, db: AsyncSession, product_id: UUID, product_in: ProductUpdate) -> dict[str, Any]:
        product = await crud_products.get(db=db, id=product_id, is_deleted=False)
        if not product:
            raise ResourceNotFoundError(f"Product with ID {product_id} not found")
        if product_in.slug and product_in.slug != product.get("slug"):
            existing = await crud_products.get(db=db, slug=product_in.slug)
            if existing:
                raise ResourceExistsError(f"Product with slug '{product_in.slug}' already exists")
        return await crud_products.update(db=db, object=product_in, id=product_id)

    async def delete(self, db: AsyncSession, product_id: UUID) -> None:
        product = await crud_products.get(db=db, id=product_id, is_deleted=False)
        if not product:
            raise ResourceNotFoundError(f"Product with ID {product_id} not found")
        await crud_products.delete(db=db, id=product_id)


class ImageService:
    async def create(self, db: AsyncSession, image_in: ProductImageCreate) -> dict[str, Any]:
        return await crud_images.create(db=db, object=image_in)

    async def delete(self, db: AsyncSession, image_id: UUID) -> None:
        image = await crud_images.get(db=db, id=image_id, is_deleted=False)
        if not image:
            raise ResourceNotFoundError(f"Image with ID {image_id} not found")
        await crud_images.delete(db=db, id=image_id)


class VariantService:
    async def create(self, db: AsyncSession, variant_in: ProductVariantCreate) -> dict[str, Any]:
        return await crud_variants.create(db=db, object=variant_in)

    async def update(self, db: AsyncSession, variant_id: UUID, variant_in: ProductVariantCreate) -> dict[str, Any]:
        variant = await crud_variants.get(db=db, id=variant_id, is_deleted=False)
        if not variant:
            raise ResourceNotFoundError(f"Variant with ID {variant_id} not found")
        return await crud_variants.update(db=db, object=variant_in, id=variant_id)

    async def delete(self, db: AsyncSession, variant_id: UUID) -> None:
        variant = await crud_variants.get(db=db, id=variant_id, is_deleted=False)
        if not variant:
            raise ResourceNotFoundError(f"Variant with ID {variant_id} not found")
        await crud_variants.delete(db=db, id=variant_id)


class ColorService:
    async def create(self, db: AsyncSession, color_in: ProductColorCreate) -> dict[str, Any]:
        return await crud_colors.create(db=db, object=color_in)

    async def update(self, db: AsyncSession, color_id: UUID, color_in: ProductColorCreate) -> dict[str, Any]:
        color = await crud_colors.get(db=db, id=color_id, is_deleted=False)
        if not color:
            raise ResourceNotFoundError(f"Color with ID {color_id} not found")
        return await crud_colors.update(db=db, object=color_in, id=color_id)

    async def delete(self, db: AsyncSession, color_id: UUID) -> None:
        color = await crud_colors.get(db=db, id=color_id, is_deleted=False)
        if not color:
            raise ResourceNotFoundError(f"Color with ID {color_id} not found")
        await crud_colors.delete(db=db, id=color_id)


product_service = ProductService()
image_service = ImageService()
variant_service = VariantService()
color_service = ColorService()
