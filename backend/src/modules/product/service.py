from typing import Any

from sqlalchemy import select
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
from .models import PriceProductSetting, Product, ProductVariant
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
                "width": v.width,
                "length": v.length,
                "height": v.height,
                "weight": v.weight,
                "price": v.price,
                "stock_qty": v.stock_qty,
                "min_order_qty": v.min_order_qty,
                "sort_order": v.sort_order,
                "status": v.status,
                "creator": v.creator,
                "editor": v.editor,
                "deleted": v.deleted,
                "created_at": v.created_at,
                "updated_at": v.updated_at,
                "price_product_settings": [],
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
        "width": variant.width,
        "length": variant.length,
        "height": variant.height,
        "weight": variant.weight,
        "price": variant.price,
        "stock_qty": variant.stock_qty,
        "min_order_qty": variant.min_order_qty,
        "sort_order": variant.sort_order,
        "status": variant.status,
        "creator": variant.creator,
        "editor": variant.editor,
        "deleted": variant.deleted,
        "created_at": variant.created_at,
        "updated_at": variant.updated_at,
        "price_product_settings": [],
    }


class ProductService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        stmt = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.price_product_settings).selectinload(PriceProductSetting.volume_tiers),
                selectinload(Product.colors),
                selectinload(Product.price_product_settings).selectinload(PriceProductSetting.volume_tiers),
                selectinload(Product.reviews),
            )
            .where(not Product.is_deleted)
            .offset(skip)
            .limit(limit)
        )
        for key, value in filters.items():
            if hasattr(Product, key):
                stmt = stmt.where(getattr(Product, key) == value)
        result = await db.execute(stmt)
        products = result.scalars().all()
        total = len(products)
        return {
            "data": [_product_to_dict(p) for p in products],
            "count": total,
            "has_more": total == limit,
        }

    async def get_by_id(self, db: AsyncSession, product_id: int) -> dict[str, Any]:
        stmt = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.price_product_settings).selectinload(PriceProductSetting.volume_tiers),
                selectinload(Product.colors),
                selectinload(Product.price_product_settings).selectinload(PriceProductSetting.volume_tiers),
                selectinload(Product.reviews),
            )
            .where(Product.id == product_id, not Product.is_deleted)
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            raise ResourceNotFoundError(f"Product with ID {product_id} not found")

        product_dict = _product_to_dict(product)
        product_dict["price_product_settings"] = [
            {
                "id": pps.id,
                "code": pps.code,
                "title": pps.title,
                "description": pps.description,
                "type": pps.type,
                "scope": pps.scope,
                "discount_type": pps.discount_type,
                "discount_value": pps.discount_value,
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
            for pps in (product.price_product_settings or [])
        ]

        variant_map = {v.id: v for v in (product.variants or [])}
        for variant in product_dict.get("variants", []):
            variant_id = variant["id"]
            v = variant_map.get(variant_id)
            if v:
                variant["price_product_settings"] = [
                    {
                        "id": pps.id,
                        "code": pps.code,
                        "title": pps.title,
                        "description": pps.description,
                        "type": pps.type,
                        "scope": pps.scope,
                        "discount_type": pps.discount_type,
                        "discount_value": pps.discount_value,
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
                    for pps in (v.price_product_settings or [])
                ]

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

    async def update(self, db: AsyncSession, product_id: int, product_in: ProductUpdate) -> dict[str, Any]:
        product = await crud_products.get(db=db, id=product_id, is_deleted=False)
        if not product:
            raise ResourceNotFoundError(f"Product with ID {product_id} not found")
        if product_in.slug and product_in.slug != product.get("slug"):
            existing = await crud_products.get(db=db, slug=product_in.slug)
            if existing:
                raise ResourceExistsError(f"Product with slug '{product_in.slug}' already exists")
        return await crud_products.update(db=db, object=product_in, id=product_id)

    async def delete(self, db: AsyncSession, product_id: int) -> None:
        product = await crud_products.get(db=db, id=product_id, is_deleted=False)
        if not product:
            raise ResourceNotFoundError(f"Product with ID {product_id} not found")
        await crud_products.delete(db=db, id=product_id)


class ImageService:
    async def create(self, db: AsyncSession, image_in: ProductImageCreate) -> dict[str, Any]:
        return await crud_images.create(db=db, object=image_in)

    async def delete(self, db: AsyncSession, image_id: int) -> None:
        image = await crud_images.get(db=db, id=image_id, is_deleted=False)
        if not image:
            raise ResourceNotFoundError(f"Image with ID {image_id} not found")
        await crud_images.delete(db=db, id=image_id)


class VariantService:
    async def create(self, db: AsyncSession, variant_in: ProductVariantCreate) -> dict[str, Any]:
        return await crud_variants.create(db=db, object=variant_in)

    async def update(self, db: AsyncSession, variant_id: int, variant_in: ProductVariantCreate) -> dict[str, Any]:
        variant = await crud_variants.get(db=db, id=variant_id, is_deleted=False)
        if not variant:
            raise ResourceNotFoundError(f"Variant with ID {variant_id} not found")
        return await crud_variants.update(db=db, object=variant_in, id=variant_id)

    async def delete(self, db: AsyncSession, variant_id: int) -> None:
        variant = await crud_variants.get(db=db, id=variant_id, is_deleted=False)
        if not variant:
            raise ResourceNotFoundError(f"Variant with ID {variant_id} not found")
        await crud_variants.delete(db=db, id=variant_id)


class ColorService:
    async def create(self, db: AsyncSession, color_in: ProductColorCreate) -> dict[str, Any]:
        return await crud_colors.create(db=db, object=color_in)

    async def update(self, db: AsyncSession, color_id: int, color_in: ProductColorCreate) -> dict[str, Any]:
        color = await crud_colors.get(db=db, id=color_id, is_deleted=False)
        if not color:
            raise ResourceNotFoundError(f"Color with ID {color_id} not found")
        return await crud_colors.update(db=db, object=color_in, id=color_id)

    async def delete(self, db: AsyncSession, color_id: int) -> None:
        color = await crud_colors.get(db=db, id=color_id, is_deleted=False)
        if not color:
            raise ResourceNotFoundError(f"Color with ID {color_id} not found")
        await crud_colors.delete(db=db, id=color_id)


product_service = ProductService()
image_service = ImageService()
variant_service = VariantService()
color_service = ColorService()
