import re
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from ..common.utils import get_media_url
from .crud import (
    crud_colors,
    crud_images,
    crud_products,
    crud_variants,
)
from .models import (
    PriceProductSetting,
    PriceProductSettingItem,
    Product,
    ProductTag,
    ProductTagRelation,
    ProductVariant,
)
from .schemas import (
    ProductColorCreate,
    ProductCreate,
    ProductImageCreate,
    ProductUpdate,
    ProductVariantCreate,
)

logger = get_logger()


def _safe_uuid(val: Any) -> UUID | None:
    if not val:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val).strip())
    except (ValueError, TypeError):
        return None


def _natural_sort_key(s: Any) -> list[int | str]:
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]


def _normalize_variant_attributes(attrs: dict[str, Any] | None, variant_name: str | None = None) -> dict[str, Any]:
    res = dict(attrs) if attrs else {}
    comp = res.get("Kelengkapan")
    if comp or variant_name:
        comp_str = (str(comp or "") + " " + str(variant_name or "")).lower()
        if "full" in comp_str or "divan" in comp_str or "set" in comp_str:
            res["Kelengkapan"] = "Fullset"
        else:
            res["Kelengkapan"] = "Mattress Only"
    return res


def _parse_variant_info(
    attrs: dict[str, Any] | None,
    variant_name: str | None = None,
    width: Any = None,
    length: Any = None,
    height: Any = None,
) -> dict[str, Any]:
    attrs = dict(attrs) if attrs else {}
    name = (variant_name or "").strip()

    # 1. Determine Size (Ukuran)
    size = None
    if attrs.get("Ukuran"):
        size = str(attrs["Ukuran"]).strip().upper()

    if not size and name:
        m = re.match(r"^(\d+\s*[xX×]\s*\d+)", name)
        if m:
            size = m.group(1).upper()

    if not size:
        w = attrs.get("width") if attrs.get("width") is not None else width
        l = attrs.get("length") if attrs.get("length") is not None else length
        try:
            if w is not None and l is not None and float(w) > 0 and float(l) > 0:
                w_val = int(float(w))
                l_val = int(float(l))
                w_str = f"{w_val:03d}" if w_val < 100 else f"{w_val}"
                size = f"{w_str} X {l_val}"
        except (ValueError, TypeError):
            pass

    if not size and name:
        m_any = re.search(r"(\d+\s*[xX×]\s*\d+)", name)
        if m_any:
            size = m_any.group(1).upper()

    if not size:
        size = name or "Standar"

    # Normalize "X" spacing and zero pad 2-digit width e.g. "80 X 200" -> "080 X 200"
    m_sz = re.match(r"^(\d+)\s*[xX×]\s*(\d+)$", size)
    if m_sz:
        w_int = int(m_sz.group(1))
        l_int = int(m_sz.group(2))
        w_str = f"{w_int:03d}" if w_int < 100 else f"{w_int}"
        size = f"{w_str} X {l_int}"

    # 2. Determine Completeness (Kelengkapan) - strictly 'Mattress Only' or 'Fullset'
    comp_raw = attrs.get("Kelengkapan")
    comp_str = f"{comp_raw or ''} {name}".lower()
    if any(k in comp_str for k in ["full", "divan", "set"]):
        kelengkapan = "Fullset"
    else:
        kelengkapan = "Mattress Only"

    # 3. Determine Thickness (Ketebalan / Tebal)
    thickness = None
    if attrs.get("Ketebalan"):
        thickness = str(attrs["Ketebalan"]).strip()
    elif attrs.get("tebal"):
        thickness = str(attrs["tebal"]).strip()
    else:
        h = attrs.get("height") if attrs.get("height") is not None else height
        try:
            if h is not None and float(h) > 0:
                h_val = int(float(h)) if float(h).is_integer() else float(h)
                thickness = f"{h_val} cm"
        except (ValueError, TypeError):
            pass

    if not thickness and name:
        m_t = re.search(r"\b(?:T|Tebal)\.?\s*(\d+)", name, re.IGNORECASE)
        if m_t:
            thickness = f"{m_t.group(1)} cm"

    return {
        "size": size,
        "kelengkapan": kelengkapan,
        "thickness": thickness or "-",
    }


def _build_product_groups(product_dict: dict[str, Any]) -> None:
    variants = product_dict.get("variants", [])
    if not variants:
        product_dict["grouped_variants"] = []
        product_dict["attribute_groups"] = {}
        return

    groups_by_size: dict[str, list[dict[str, Any]]] = {}
    sizes_set = set()
    kelengkapan_set = set()
    thickness_set = set()

    for v in variants:
        attrs = v.get("attributes") or {}
        v_name = v.get("variant_name") or ""
        parsed = _parse_variant_info(
            attrs=attrs,
            variant_name=v_name,
            width=v.get("width"),
            length=v.get("length"),
            height=v.get("height"),
        )

        v["size"] = parsed["size"]
        v["kelengkapan"] = parsed["kelengkapan"]
        v["thickness"] = parsed["thickness"]
        v["tebal"] = parsed["thickness"]
        if "attributes" in v and isinstance(v["attributes"], dict):
            v["attributes"]["Ukuran"] = parsed["size"]
            v["attributes"]["Kelengkapan"] = parsed["kelengkapan"]
            if parsed["thickness"] != "-":
                v["attributes"]["Ketebalan"] = parsed["thickness"]

        sz = parsed["size"]
        groups_by_size.setdefault(sz, []).append(v)
        sizes_set.add(sz)
        kelengkapan_set.add(parsed["kelengkapan"])
        if parsed["thickness"] != "-":
            thickness_set.add(parsed["thickness"])

    sorted_sizes = sorted(groups_by_size.keys(), key=_natural_sort_key)

    grouped_variants = []
    for sz in sorted_sizes:
        var_list = groups_by_size[sz]
        var_list.sort(key=lambda item: (
            item["kelengkapan"] != "Mattress Only",
            _natural_sort_key(item["thickness"]),
            _natural_sort_key(item.get("variant_name") or "")
        ))

        prices = [
            float(v.get("final_price") or v.get("sell_price") or 0.0)
            for v in var_list
            if float(v.get("sell_price") or 0.0) > 0
        ]
        if not prices:
            prices = [float(v.get("sell_price") or 0.0) for v in var_list]
        min_p = min(prices) if prices else 0.0
        max_p = max(prices) if prices else 0.0
        stock = sum(int(v.get("stock_qty") or 0) for v in var_list)

        ship_costs = [
            float(v.get("shipping_cost") or 0.0)
            for v in var_list
            if v.get("shipping_cost") is not None
        ]
        min_ship = min(ship_costs) if ship_costs else float(product_dict.get("shipping_cost") or 0.0)
        max_ship = max(ship_costs) if ship_costs else float(product_dict.get("shipping_cost") or 0.0)

        comps = sorted(list({v["kelengkapan"] for v in var_list}))
        thicks = sorted(list({v["thickness"] for v in var_list if v["thickness"] != "-"}))

        grouped_variants.append({
            "size": sz,
            "min_price": min_p,
            "max_price": max_p,
            "min_shipping_cost": min_ship,
            "max_shipping_cost": max_ship,
            "total_stock": stock,
            "completenesses": comps,
            "thicknesses": thicks,
            "image": next((v.get("image") for v in var_list if v.get("image")), None),
            "image_url": next((v.get("image_url") for v in var_list if v.get("image_url")), None),
            "variants": var_list,
        })

    product_dict["grouped_variants"] = grouped_variants
    product_dict["attribute_groups"] = {
        "Ukuran": sorted(list(sizes_set), key=_natural_sort_key),
        "Kelengkapan": sorted(list(kelengkapan_set)),
        "Ketebalan": sorted(list(thickness_set), key=_natural_sort_key),
    }


def _product_to_dict(product: Product) -> dict[str, Any]:
    thumb_url = get_media_url(product.thumbnail)
    c_type = getattr(product, "courier_type", "keduanya") or "keduanya"
    s_scheme = getattr(product, "shipping_scheme", "dimension") or "dimension"
    s_cost = float(getattr(product, "shipping_cost", 0.0) or 0.0)

    courier_labels = {
        "toko": "Pengiriman by Toko",
        "expedisi": "Pengiriman by Expedisi",
        "keduanya": "Keduanya (Toko & Expedisi)",
    }
    scheme_labels = {
        "fixed": "Ongkos Kirim Tetap (Fixed Rate)",
        "dimension": "Hitung dari Dimensi & Berat",
    }

    all_images = [
        {
            "id": img.id,
            "product_id": img.product_id,
            "image": get_media_url(img.image),
            "image_url": get_media_url(img.image),
            "alt_text": img.alt_text,
            "variant_id": img.variant_id,
            "created_at": img.created_at,
            "updated_at": img.updated_at,
        }
        for img in (product.images or [])
        if not getattr(img, "deleted", False)
    ]
    header_images = [img for img in all_images if img["variant_id"] is None]

    variant_images_map: dict[str, list[dict[str, Any]]] = {}
    for img in all_images:
        if img["variant_id"]:
            variant_images_map.setdefault(str(img["variant_id"]), []).append(img)

    variants_list = []
    for v in (product.variants or []):
        if getattr(v, "deleted", False):
            continue
        v_imgs = variant_images_map.get(str(v.id), [])
        if not v_imgs and getattr(v, "images", None):
            v_imgs = [
                {
                    "id": img.id,
                    "product_id": img.product_id,
                    "image": get_media_url(img.image),
                    "image_url": get_media_url(img.image),
                    "alt_text": img.alt_text,
                    "variant_id": img.variant_id,
                    "created_at": img.created_at,
                    "updated_at": img.updated_at,
                }
                for img in v.images
                if not getattr(img, "deleted", False)
            ]
        v_primary_img = None
        if v_imgs:
            v_primary_img = v_imgs[0]["image_url"]
        elif v.attributes and v.attributes.get("image"):
            v_primary_img = get_media_url(v.attributes.get("image"))
        elif v.attributes and v.attributes.get("image_url"):
            v_primary_img = get_media_url(v.attributes.get("image_url"))

        v_dict = {
            "id": v.id,
            "product_id": v.product_id,
            "sku": v.sku,
            "variant_name": v.variant_name,
            "base_price": v.base_price,
            "sell_price": v.sell_price,
            "shipping_cost": float(getattr(v, "shipping_cost", 0.0) or 0.0),
            "stock_qty": v.stock_qty,
            "attributes": _normalize_variant_attributes(v.attributes, v.variant_name),
            "image": v_primary_img,
            "image_url": v_primary_img,
            "images": v_imgs,
            "width": (v.attributes or {}).get("width") if v.attributes and (v.attributes.get("width") is not None) else getattr(v, "width", None),
            "length": (v.attributes or {}).get("length") if v.attributes and (v.attributes.get("length") is not None) else getattr(v, "length", None),
            "height": (v.attributes or {}).get("height") if v.attributes and (v.attributes.get("height") is not None) else getattr(v, "height", None),
            "weight": (v.attributes or {}).get("weight") if v.attributes and (v.attributes.get("weight") is not None) else getattr(v, "weight", None),
            "status": getattr(v, "status", True) if getattr(v, "status", None) is not None else ((v.attributes or {}).get("status", True) if v.attributes else True),
            "creator": v.creator,
            "editor": v.editor,
            "deleted": v.deleted,
            "created_at": v.created_at,
            "updated_at": v.updated_at,
            "price_product_settings": [],
            "final_price": 0.0,
        }
        variants_list.append(v_dict)

    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "category_id": product.category_id,
        "thumbnail": thumb_url,
        "thumbnail_url": thumb_url,
        "alt_text": product.alt_text,
        "short_description": product.short_description,
        "description": product.description,
        "code": getattr(product, "code", None),
        "warranty_duration": getattr(product, "warranty_duration", None),
        "courier_type": c_type,
        "courier_type_label": courier_labels.get(c_type, "Keduanya (Toko & Expedisi)"),
        "shipping_scheme": s_scheme,
        "shipping_scheme_label": scheme_labels.get(s_scheme, "Hitung dari Dimensi & Berat"),
        "shipping_cost": s_cost,
        "length": getattr(product, "length", None),
        "width": getattr(product, "width", None),
        "height": getattr(product, "height", None),
        "weight": getattr(product, "weight", None),
        "segments": product.segments,
        "best_seller": product.best_seller,
        "is_new": product.is_new,
        "status": product.status,
        "creator": product.creator,
        "editor": product.editor,
        "deleted": product.deleted,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "images": all_images,
        "header_images": header_images,
        "variants": variants_list,
        "colors": [
            {
                "id": c.id,
                "product_id": c.product_id,
                "color_name": c.color_name,
                "color_code": c.color_code,
                "status": getattr(c, "status", True),
                "creator": c.creator,
                "editor": c.editor,
                "deleted": c.deleted,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in (product.colors or [])
            if not getattr(c, "deleted", False)
        ],
        "grouped_variants": [],
        "attribute_groups": {},
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
                "image_url": get_media_url(r.image_url),
                "is_approved": r.is_approved,
                "is_published": r.is_published,
                "report_count": r.report_count,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "deleted": r.deleted,
            }
            for r in (product.reviews or [])
        ],
        "suggestions": [
            {
                "id": s.id,
                "name": s.name,
                "slug": s.slug,
                "thumbnail": get_media_url(s.thumbnail),
                "thumbnail_url": get_media_url(s.thumbnail),
                "alt_text": s.alt_text,
            }
            for s in (getattr(product, "suggestions", []) or [])
        ],
        "tag_ids": [],
        "tags": [],
    }
    _build_product_groups(res)
    return res


def _variant_to_dict(variant: ProductVariant) -> dict[str, Any]:
    v_imgs = [
        {
            "id": img.id,
            "product_id": img.product_id,
            "image": get_media_url(img.image),
            "image_url": get_media_url(img.image),
            "alt_text": img.alt_text,
            "variant_id": img.variant_id,
            "created_at": img.created_at,
            "updated_at": img.updated_at,
        }
        for img in (getattr(variant, "images", []) or [])
        if not getattr(img, "deleted", False)
    ]
    primary_img = None
    if v_imgs:
        primary_img = v_imgs[0]["image_url"]
    elif variant.attributes and variant.attributes.get("image"):
        primary_img = get_media_url(variant.attributes.get("image"))
    elif variant.attributes and variant.attributes.get("image_url"):
        primary_img = get_media_url(variant.attributes.get("image_url"))

    res = {
        "id": variant.id,
        "product_id": variant.product_id,
        "sku": variant.sku,
        "variant_name": variant.variant_name,
        "price": variant.price,
        "base_price": getattr(variant, "base_price", variant.price),
        "sell_price": getattr(variant, "sell_price", variant.price),
        "shipping_cost": float(getattr(variant, "shipping_cost", 0.0) or 0.0),
        "stock_qty": variant.stock_qty,
        "attributes": _normalize_variant_attributes(variant.attributes, variant.variant_name),
        "image": primary_img,
        "image_url": primary_img,
        "images": v_imgs,
        "width": (variant.attributes or {}).get("width") if variant.attributes and (variant.attributes.get("width") is not None) else getattr(variant, "width", None),
        "length": (variant.attributes or {}).get("length") if variant.attributes and (variant.attributes.get("length") is not None) else getattr(variant, "length", None),
        "height": (variant.attributes or {}).get("height") if variant.attributes and (variant.attributes.get("height") is not None) else getattr(variant, "height", None),
        "weight": (variant.attributes or {}).get("weight") if variant.attributes and (variant.attributes.get("weight") is not None) else getattr(variant, "weight", None),
        "status": getattr(variant, "status", True) if getattr(variant, "status", None) is not None else ((variant.attributes or {}).get("status", True) if variant.attributes else True),
        "creator": variant.creator,
        "editor": variant.editor,
        "deleted": variant.deleted,
        "created_at": variant.created_at,
        "updated_at": variant.updated_at,
        "price_product_settings": [],
        "final_price": 0.0,
    }
    parsed = _parse_variant_info(
        attrs=res["attributes"],
        variant_name=res["variant_name"],
        width=res["width"],
        length=res["length"],
        height=res["height"],
    )
    res["size"] = parsed["size"]
    res["kelengkapan"] = parsed["kelengkapan"]
    res["thickness"] = parsed["thickness"]
    res["tebal"] = parsed["thickness"]
    return res


def _price_setting_item_to_dict(item: PriceProductSettingItem) -> dict[str, Any]:
    pps = item.setting
    if not pps:
        return {}
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
        "image_url": get_media_url(pps.image_url),
        "is_active": pps.is_active,
        "is_featured": pps.is_featured,
        "sort_order": getattr(pps, "sort_order", 0),
        "volume_tiers": [
            {
                "id": vt.id,
                "min_purchase": vt.min_purchase,
                "discount_type": vt.discount_type,
                "discount_value": vt.discount_value,
                "sort_order": getattr(vt, "sort_order", 0),
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
                selectinload(Product.suggestions),
            )
            .where(
                Product.deleted.is_(False),
                or_(Product.show_on_web == True, Product.show_on_web.is_(None)),
                Product.variants.any(ProductVariant.sell_price > 0)
            )
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(Product).where(
            Product.deleted.is_(False),
            or_(Product.show_on_web == True, Product.show_on_web.is_(None)),
            Product.variants.any(ProductVariant.sell_price > 0)
        )

        for key, value in filters.items():
            if key in ("category_id", "category_id__eq"):
                cond = or_(Product.category_id == value, Product.brand_id == value)
                query = query.where(cond)
                count_query = count_query.where(cond)
            elif key in ("tag_id", "tag_id__eq"):
                tag_uuid = _safe_uuid(value) or value
                tag_cond = Product.id.in_(
                    select(ProductTagRelation.product_id).where(
                        ProductTagRelation.tag_id == tag_uuid,
                        ProductTagRelation.deleted == False,
                    )
                )
                query = query.where(tag_cond)
                count_query = count_query.where(tag_cond)
            elif key in ("tag_ids", "tag_ids__in"):
                tag_list = []
                if isinstance(value, str):
                    tag_list = [v.strip() for v in value.split(",") if v.strip()]
                elif isinstance(value, (list, set, tuple)):
                    tag_list = list(value)
                valid_tag_uuids = [_safe_uuid(t) or t for t in tag_list if t]
                if valid_tag_uuids:
                    tag_cond = Product.id.in_(
                        select(ProductTagRelation.product_id).where(
                            ProductTagRelation.tag_id.in_(valid_tag_uuids),
                            ProductTagRelation.deleted == False,
                        )
                    )
                    query = query.where(tag_cond)
                    count_query = count_query.where(tag_cond)
            elif "__" in key:
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

        tags_by_product: dict[UUID, list[dict[str, Any]]] = {}
        if products:
            product_ids = [p.id for p in products]
            tags_stmt = (
                select(ProductTagRelation, ProductTag)
                .join(ProductTag, ProductTag.id == ProductTagRelation.tag_id)
                .where(
                    ProductTagRelation.product_id.in_(product_ids),
                    ProductTagRelation.deleted == False,
                    ProductTag.deleted == False,
                )
                .order_by(ProductTag.sort_order.asc(), ProductTag.name.asc())
            )
            tags_res = await db.execute(tags_stmt)
            for rel, tag in tags_res.all():
                tags_by_product.setdefault(rel.product_id, []).append({
                    "id": str(tag.id),
                    "name": tag.name,
                    "slug": tag.slug,
                    "sort_order": tag.sort_order,
                })

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
                0.0,
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
                        float(v.sell_price or 0),
                        variant["price_product_settings"],
                    )

            reviews = product_dict.get("reviews", [])
            avg_rating = (
                sum(r["rating"] for r in reviews if r.get("rating")) / len(reviews) if reviews else 0
            )
            product_dict["avg_rating"] = round(avg_rating, 2)
            prod_tags = tags_by_product.get(product.id, [])
            product_dict["tags"] = prod_tags
            product_dict["tag_ids"] = [t["id"] for t in prod_tags]
            _build_product_groups(product_dict)
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
                selectinload(Product.suggestions),
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
            0.0,
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
                    float(v.sell_price or 0),
                    variant["price_product_settings"],
                )

        reviews = product_dict.get("reviews", [])
        avg_rating = (
            sum(r["rating"] for r in reviews if r.get("rating")) / len(reviews) if reviews else 0
        )
        product_dict["avg_rating"] = round(avg_rating, 2)
        product_dict["total_reviews"] = len(reviews)

        tags_stmt = (
            select(ProductTag)
            .join(ProductTagRelation, ProductTagRelation.tag_id == ProductTag.id)
            .where(
                ProductTagRelation.product_id == product_id,
                ProductTagRelation.deleted == False,
                ProductTag.deleted == False,
            )
            .order_by(ProductTag.sort_order.asc(), ProductTag.name.asc())
        )
        tags_res = await db.execute(tags_stmt)
        prod_tags = [
            {
                "id": str(t.id),
                "name": t.name,
                "slug": t.slug,
                "sort_order": t.sort_order,
            }
            for t in tags_res.scalars().all()
        ]
        product_dict["tags"] = prod_tags
        product_dict["tag_ids"] = [t["id"] for t in prod_tags]

        _build_product_groups(product_dict)
        return product_dict

    async def create(self, db: AsyncSession, product_in: ProductCreate) -> dict[str, Any]:
        existing = await crud_products.get(db=db, slug=product_in.slug)
        if existing:
            raise ResourceExistsError(f"Product with slug '{product_in.slug}' already exists")
        return await crud_products.create(db=db, object=product_in)

    async def update(self, db: AsyncSession, product_id: UUID, product_in: ProductUpdate) -> dict[str, Any]:
        product = await crud_products.get(db=db, id=product_id, deleted=False)
        if not product:
            raise ResourceNotFoundError(f"Product with ID {product_id} not found")
        if product_in.slug and product_in.slug != product.get("slug"):
            existing = await crud_products.get(db=db, slug=product_in.slug)
            if existing:
                raise ResourceExistsError(f"Product with slug '{product_in.slug}' already exists")
        return await crud_products.update(db=db, object=product_in, id=product_id)

    async def delete(self, db: AsyncSession, product_id: UUID) -> None:
        product = await crud_products.get(db=db, id=product_id, deleted=False)
        if not product:
            raise ResourceNotFoundError(f"Product with ID {product_id} not found")
        await crud_products.delete(db=db, id=product_id)


class ImageService:
    async def create(self, db: AsyncSession, image_in: ProductImageCreate) -> dict[str, Any]:
        return await crud_images.create(db=db, object=image_in)

    async def delete(self, db: AsyncSession, image_id: UUID) -> None:
        image = await crud_images.get(db=db, id=image_id, deleted=False)
        if not image:
            raise ResourceNotFoundError(f"Image with ID {image_id} not found")
        await crud_images.delete(db=db, id=image_id)


class VariantService:
    async def create(self, db: AsyncSession, variant_in: ProductVariantCreate) -> dict[str, Any]:
        return await crud_variants.create(db=db, object=variant_in)

    async def update(self, db: AsyncSession, variant_id: UUID, variant_in: ProductVariantCreate) -> dict[str, Any]:
        variant = await crud_variants.get(db=db, id=variant_id, deleted=False)
        if not variant:
            raise ResourceNotFoundError(f"Variant with ID {variant_id} not found")
        return await crud_variants.update(db=db, object=variant_in, id=variant_id)

    async def delete(self, db: AsyncSession, variant_id: UUID) -> None:
        variant = await crud_variants.get(db=db, id=variant_id, deleted=False)
        if not variant:
            raise ResourceNotFoundError(f"Variant with ID {variant_id} not found")
        await crud_variants.delete(db=db, id=variant_id)


class ColorService:
    async def create(self, db: AsyncSession, color_in: ProductColorCreate) -> dict[str, Any]:
        return await crud_colors.create(db=db, object=color_in)

    async def update(self, db: AsyncSession, color_id: UUID, color_in: ProductColorCreate) -> dict[str, Any]:
        color = await crud_colors.get(db=db, id=color_id, deleted=False)
        if not color:
            raise ResourceNotFoundError(f"Color with ID {color_id} not found")
        return await crud_colors.update(db=db, object=color_in, id=color_id)

    async def delete(self, db: AsyncSession, color_id: UUID) -> None:
        color = await crud_colors.get(db=db, id=color_id, deleted=False)
        if not color:
            raise ResourceNotFoundError(f"Color with ID {color_id} not found")
        await crud_colors.delete(db=db, id=color_id)


product_service = ProductService()
image_service = ImageService()
variant_service = VariantService()
color_service = ColorService()
