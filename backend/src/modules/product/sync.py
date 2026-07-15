import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from taskiq import TaskiqDepends

from ...infrastructure.logging.receiver import get_receiver_logger
from ...infrastructure.taskiq.brokers import default_broker
from ...infrastructure.taskiq.deps import get_db_session
from ..category.models import Category
from .models import Product, ProductColor, ProductImage, ProductVariant, Brand, RefProductCategory

# Dedicated daily-rotating logger for the product (item-master) receiver
logger = get_receiver_logger("product", "item-master")


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


def safe_float(val: Any) -> float:
    """Safely convert JDE segment or price to float."""
    if not val or str(val).strip() == "":
        return 0.0
    try:
        cleaned = re.sub(r"[^\d.,-]", "", str(val).strip())
        return float(cleaned.replace(",", ""))
    except ValueError:
        return 0.0


async def resolve_brand_id(db: AsyncSession, brand_code: str | None) -> uuid.UUID:
    """Resolve brand ID from payload brand_id (matched against brands table by slug).

    If brand_code is empty, falls back to the first existing brand or creates a
    default "Royal Foam" brand. If a matching brand is not found, a new brand is
    created.
    """
    if not brand_code or not str(brand_code).strip():
        # Fallback: reuse first existing brand or create default "Royal Foam"
        stmt = select(Brand)
        res = await db.execute(stmt)
        existing_brand = res.scalars().first()
        if existing_brand:
            return existing_brand.id

        default_brand_id = uuid.UUID("311c97a8-1296-4113-9111-c9183491411b")
        brand = Brand(
            id=default_brand_id,
            name="Royal Foam",
            slug="royal-foam",
            status=1,
            deleted=False,
        )
        db.add(brand)
        await db.flush()
        logger.info(f"Membuat brand default baru: Royal Foam ({default_brand_id})")
        return default_brand_id

    brand_code = str(brand_code).strip()
    brand_slug = slugify(brand_code)

    stmt = select(Brand).where(Brand.slug == brand_slug)
    res = await db.execute(stmt)
    brand = res.scalar_one_or_none()

    if not brand:
        brand = Brand(name=brand_code, slug=brand_slug, status=1, deleted=False)
        db.add(brand)
        await db.flush()
        logger.info(f"Membuat brand baru: {brand_code} ({brand.id})")

    return brand.id


SEGMENT1_CATEGORY_FALLBACK = {
    "DV": "Divan",
    "EB": "Bolster",
    "EM": "Travel Mate",
    "ER": "Protector",
    "HB": "Headboard",
}


async def resolve_category_id(db: AsyncSession, row: dict[str, Any]) -> uuid.UUID:
    """Resolve category ID from payload.

    Priority:
    1. Explicit ``template`` name (backward compatible).
    2. ``segments.segment1`` matched against ``ref_product_categories.code``;
       the reference table's ``name`` is then used to find/create a Category.
    3. Fallback mapping of segment1 to a known category name.
    """
    category_name = (row.get("template") or "").strip()

    if not category_name:
        segments = row.get("segments", {})
        if not isinstance(segments, dict):
            segments = {}
        seg1 = (segments.get("segment1") or "").strip().upper()

        if seg1:
            ref_stmt = select(RefProductCategory).where(RefProductCategory.code == seg1)
            ref_res = await db.execute(ref_stmt)
            ref = ref_res.scalar_one_or_none()
            if ref and ref.name:
                category_name = ref.name.strip()

        if not category_name:
            category_name = SEGMENT1_CATEGORY_FALLBACK.get(seg1, "BJ MATRASS")

    if not category_name:
        category_name = "BJ MATRASS"

    category_slug = slugify(category_name)

    # Resolve by slug (the unique key) so name variations that slugify to the
    # same slug (e.g. "Royal" vs "ROYAL ") reuse the existing category instead
    # of violating the unique slug constraint on insert.
    stmt = select(Category).where(Category.slug == category_slug)
    res = await db.execute(stmt)
    category = res.scalar_one_or_none()

    if not category:
        category = Category(
            name=category_name,
            slug=category_slug,
            status=True,
            description=f"Automatically created from POS sync for category: {category_name}",
        )
        db.add(category)
        await db.flush()

    return category.id


async def sync_products_data(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute the synchronization of JDE/POS products into the database.

    Args:
        db: The active database session.
        payload: The JSON webhook payload containing rowset items.

    Returns:
        dict: A summary of the synchronization results.
    """
    # Normalize/resolve rowset from JDE payload dynamically
    if isinstance(payload, dict) and "rowset" in payload:
        rowset = payload["rowset"]
    elif isinstance(payload, dict) and "data" in payload:
        rowset = payload["data"]
    else:
        # Try to find a key that starts with "POS_" or contains "rowset"/"data"
        pos_key = next((k for k in payload.keys() if k.startswith("POS_")), None)
        if not pos_key:
            pos_key = next((k for k, v in payload.items() if isinstance(v, dict) and ("rowset" in v or "data" in v)), None)

        if not pos_key:
            raise ValueError(
                "Format payload POS tidak valid. Tidak ditemukan data 'rowset' atau 'data' di "
                f"root atau di dalam child keys: {list(payload.keys()) if isinstance(payload, dict) else type(payload)}"
            )

        v = payload[pos_key]
        if isinstance(v, dict):
            rowset = v.get("rowset") or v.get("data") or []
        else:
            rowset = []

    total_items = len(rowset)

    logger.info("start")
    logger.info(f"Memulai sinkronisasi POS produk. Total data mentah: {total_items}")
    if total_items > 0:
        logger.info(f"Contoh baris data pertama: {rowset[0]}")

    results = {
        "total_items": total_items,
        "grouped_products": total_items,
        "inserted_products": 0,
        "updated_products": 0,
        "inserted_variants": 0,
        "updated_variants": 0,
        "inserted_colors": 0,
        "inserted_images": 0,
        "failed_items": 0,
    }

    for item in rowset:
        product_name = item.get("name")
        product_slug = item.get("slug")
        if not product_name or not product_slug:
            logger.warning(f"Melewati baris POS karena nama atau slug kosong: {item}")
            results["failed_items"] += 1
            continue

        logger.info(f"read kode produk {product_slug}")
        logger.info(f"cek kode produk {product_slug}")

        try:
            async with db.begin_nested():
                category_id = await resolve_category_id(db, item)
                brand_id = await resolve_brand_id(db, item.get("brand_id"))

                # Query existing product with variants, colors, and images loaded
                stmt = (
                    select(Product)
                    .options(
                        selectinload(Product.variants),
                        selectinload(Product.colors),
                        selectinload(Product.images),
                    )
                    .where(Product.slug == product_slug, Product.deleted == False)  # noqa: E712
                )
                res = await db.execute(stmt)
                product = res.scalar_one_or_none()

                product_meta = item.get("segments", {})
                if not isinstance(product_meta, dict):
                    product_meta = {}
                product_meta["uom"] = item.get("uom")
                product_meta["base_price"] = item.get("base_price")

                product_is_new = False
                if product:
                    logger.info("exists")
                    # Update existing product metadata
                    product.name = product_name
                    product.category_id = category_id
                    product.brand_id = brand_id
                    product.segments = product_meta
                    product.base_price = str(item.get("base_price")) if item.get("base_price") is not None else None
                    product.uom = item.get("uom")
                    results["updated_products"] += 1
                else:
                    logger.info("not exists (creating)")
                    # Create new product
                    product = Product(
                        name=product_name,
                        slug=product_slug,
                        category_id=category_id,
                        brand_id=brand_id,
                        description=item.get("short_description") or f"Produk disinkronkan dari POS JDE: {product_name}",
                        base_price=str(item.get("base_price")) if item.get("base_price") is not None else None,
                        uom=item.get("uom"),
                        segments=product_meta,
                        status=1,
                    )
                    db.add(product)
                    await db.flush()  # Generate product.id
                    results["inserted_products"] += 1
                    product_is_new = True

                # Sync Variants
                existing_variants = {} if product_is_new else {v.sku: v for v in (product.variants or [])}
                variants_list = item.get("variants", [])
                for v_item in variants_list:
                    sku = v_item.get("sku")
                    if sku:
                        sku = sku.strip()
                    if not sku:
                        continue

                    variant_name = v_item.get("variant_name")
                    if not variant_name or not str(variant_name).strip():
                        variant_name = sku or "Standard"
                    length = safe_float(v_item.get("length"))
                    width = safe_float(v_item.get("width"))
                    price = safe_float(v_item.get("price"))

                    variant_data = {
                        "sku": sku,
                        "variant_name": variant_name,
                        "price": price,
                        "attributes": {
                            "length": length,
                            "width": width,
                            "status": True,
                        },
                    }

                    if sku in existing_variants:
                        variant = existing_variants[sku]
                        for k, v in variant_data.items():
                            setattr(variant, k, v)
                        results["updated_variants"] += 1
                    else:
                        variant = ProductVariant(product_id=product.id, **variant_data)
                        db.add(variant)
                        results["inserted_variants"] += 1

                # Sync Colors (from segment3 / Fabric) - dinonaktifkan sementara
                # existing_colors = {} if product_is_new else {c.color_code: c for c in (product.colors or [])}
                # color_code = item.get("segments", {}).get("segment3")
                # if color_code:
                #     color_code = color_code.strip()
                #
                # if color_code:
                #     if color_code not in existing_colors:
                #         color = ProductColor(
                #             product_id=product.id,
                #             color_name=f"Fabric {color_code}",
                #             color_code=color_code,
                #         )
                #         db.add(color)
                #         results["inserted_colors"] += 1

                # Sync Images (from img field)
                existing_images = {} if product_is_new else {img.image for img in (product.images or [])}
                image_url = item.get("img") or item.get("segments", {}).get("img")
                if image_url:
                    image_url = image_url.strip()

                if image_url:
                    if image_url not in existing_images:
                        product_image = ProductImage(
                            product_id=product.id,
                            image=image_url,
                            alt_text=f"Image for {product_name}",
                            status=True,
                        )
                        db.add(product_image)
                        results["inserted_images"] += 1

                # Flush periodically or at the end to optimize transaction size
                await db.flush()
                logger.info("-")

        except Exception as e:
            logger.error(f"Gagal menyelaraskan produk POS '{product_name}': {str(e)}", exc_info=True)
            results["failed_items"] += 1

    await db.commit()
    logger.info("end")
    logger.info(f"Sinkronisasi POS produk selesai: {results}")
    return results


@default_broker.task
async def sync_pos_products_task(
    payload: dict[str, Any],
    db: AsyncSession = TaskiqDepends(get_db_session),
) -> dict[str, Any]:
    """Background task to sync products from POS webhook payload."""
    try:
        return await sync_products_data(db, payload)
    except Exception as e:
        logger.error(f"Gagal dalam background task sinkronisasi produk POS: {str(e)}", exc_info=True)
        await db.rollback()
        raise e
