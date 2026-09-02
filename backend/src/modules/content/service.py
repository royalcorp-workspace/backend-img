import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.logging import get_logger
from ..category.models import Category
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from ..product.models import (
    Brand,
    PriceProductSetting,
    Product,
    ProductBundling,
    ProductBundlingItem,
    ProductImage,
    ProductVariant,
)
from .crud import (
    crud_about_us,
    crud_blog_posts,
    crud_faqs,
    crud_how_to_returns,
    crud_privacy_policies,
    crud_terms_and_conditions,
    crud_warranty_claims,
)
from .models import Banner, Event, EventPopup, HomepageSection, Notification
from .schemas import (
    AboutUsCreate,
    AboutUsRead,
    AboutUsUpdate,
    BlogPostCreate,
    BlogPostRead,
    BlogPostUpdate,
    FaqCreate,
    FaqRead,
    FaqUpdate,
    HowToReturnCreate,
    HowToReturnRead,
    HowToReturnUpdate,
    PrivacyPolicyCreate,
    PrivacyPolicyRead,
    PrivacyPolicyUpdate,
    TermsAndConditionCreate,
    TermsAndConditionRead,
    TermsAndConditionUpdate,
    WarrantyClaimCreate,
    WarrantyClaimRead,
    WarrantyClaimUpdate,
)

logger = get_logger()


class ContentService:
    # --- Homepages with Items (matching pos-dealer-web logic) ---
    async def get_homepage_sections_with_items(self, db: AsyncSession) -> list[dict[str, Any]]:
        """
        Fetch active homepage sections populated with items based on section type,
        replicating the exact business logic from pos-dealer-web HomeController.
        """
        # 1. Fetch Homepage Sections from DB
        sec_stmt = (
            select(HomepageSection)
            .where(or_(HomepageSection.is_visible.is_(True), HomepageSection.is_visible.is_(None)))
            .order_by(HomepageSection.sort_order.asc())
        )
        sec_res = await db.execute(sec_stmt)
        db_sections = sec_res.scalars().all()

        # 2. Preload Bestsellers (10 products)
        bs_stmt = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.brand),
                selectinload(Product.category),
                selectinload(Product.price_product_settings),
            )
            .where(
                Product.deleted == False,
                or_(Product.status == 1, Product.status.is_(None)),
                Product.best_seller == True,
            )
            .limit(10)
        )
        bs_res = await db.execute(bs_stmt)
        bestseller_products = bs_res.scalars().all()
        bestseller_ids = [p.id for p in bestseller_products]

        def _format_product_card(prod: Product) -> dict[str, Any]:
            valid_variants = [v for v in (prod.variants or []) if not v.deleted and (v.sell_price or 0) > 0]
            if valid_variants:
                prices = [float(v.sell_price) for v in valid_variants]
                min_price = min(prices)
                max_price = max(prices)
            else:
                min_price = float(prod.variants[0].sell_price if prod.variants and prod.variants[0].sell_price else 0.0)
                max_price = min_price

            discount_percent = 0.0
            discounted_price = min_price
            pps_label = None

            if prod.price_product_settings:
                for pps in prod.price_product_settings:
                    if getattr(pps, "is_active", True):
                        val = float(pps.discount_value or 0.0)
                        dtype = pps.discount_type
                        if dtype == 1 or (0 < val <= 100 and dtype != 2):
                            discount_percent = val
                            discounted_price = min_price * (1.0 - discount_percent / 100.0)
                            pps_label = f"{round(discount_percent)}%"
                        elif val > 0 and min_price > 0:
                            discounted_price = max(0.0, min_price - val)
                            discount_percent = round((val / min_price) * 100.0)
                            pps_label = f"{round(discount_percent)}%"
                        break

            thumb = prod.thumbnail
            if not thumb and prod.images:
                thumb = prod.images[0].image

            return {
                "id": prod.id,
                "name": prod.name,
                "slug": prod.slug,
                "thumbnail_url": thumb,
                "min_price": min_price,
                "max_price": max_price,
                "original_price": min_price,
                "discounted_price": discounted_price,
                "discount_percent": discount_percent,
                "pps_label": pps_label,
                "best_seller": prod.best_seller,
                "is_new": prod.is_new,
                "brand": (
                    {"id": prod.brand.id, "name": prod.brand.name, "slug": prod.brand.slug}
                    if prod.brand
                    else None
                ),
                "category": (
                    {"id": prod.category.id, "name": prod.category.name, "slug": prod.category.slug}
                    if prod.category
                    else None
                ),
                "images": [
                    {"id": img.id, "image_url": img.image, "alt_text": img.alt_text}
                    for img in (prod.images or [])
                ],
                "variants": [
                    {
                        "id": v.id,
                        "variant_name": v.variant_name,
                        "sku": v.sku,
                        "sell_price": float(v.sell_price or 0.0),
                        "base_price": float(v.base_price or 0.0),
                        "stock_qty": v.stock_qty or 0,
                    }
                    for v in (prod.variants or [])
                    if not v.deleted
                ],
            }

        formatted_bestsellers = [_format_product_card(p) for p in bestseller_products]

        # 3. Preload Categories (parent_id is None, limit 8)
        cat_stmt = (
            select(Category)
            .where(
                Category.deleted == False,
                or_(Category.status.is_(True), Category.status.is_(None)),
                Category.parent_id == None,
            )
            .order_by(Category.sort_order.asc())
            .limit(8)
        )
        cat_res = await db.execute(cat_stmt)
        categories = cat_res.scalars().all()
        formatted_categories = []
        for c in categories:
            cnt_stmt = select(func.count(Product.id)).where(Product.category_id == c.id, Product.deleted == False)
            cnt_res = await db.execute(cnt_stmt)
            p_count = cnt_res.scalar() or 0
            formatted_categories.append({
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "image": c.image,
                "banner_web": getattr(c, "banner_web", None),
                "banner_mobile": getattr(c, "banner_mobile", None),
                "banner": getattr(c, "banner_web", None) or getattr(c, "banner_mobile", None),
                "tagline": c.tagline,
                "description": c.description,
                "products_count": p_count,
            })

        # 4. Preload Brands
        br_stmt = (
            select(Brand)
            .where(
                Brand.deleted == False,
                or_(Brand.status == 1, Brand.status.is_(None)),
            )
            .limit(20)
        )
        br_res = await db.execute(br_stmt)
        brands = br_res.scalars().all()
        formatted_brands = [
            {
                "id": b.id,
                "name": b.name,
                "slug": b.slug,
                "logo": getattr(b, "logo", None),
                "banner_web": getattr(b, "banner_web", None),
                "banner_mobile": getattr(b, "banner_mobile", None),
                "is_featured": b.is_featured,
                "status": b.status,
            }
            for b in brands
        ]

        # 5. Preload Promo Brands (brands with top 3 discounted/promoted products)
        formatted_promo_brands = []
        for b in brands[:6]:
            b_prod_stmt = (
                select(Product)
                .options(
                    selectinload(Product.images),
                    selectinload(Product.variants),
                    selectinload(Product.brand),
                    selectinload(Product.category),
                    selectinload(Product.price_product_settings),
                )
                .where(
                    Product.brand_id == b.id,
                    Product.deleted == False,
                    or_(Product.status == 1, Product.status.is_(None)),
                )
                .limit(10)
            )
            b_prod_res = await db.execute(b_prod_stmt)
            b_prods = [_format_product_card(p) for p in b_prod_res.scalars().all()]
            b_prods.sort(key=lambda x: x.get("discount_percent", 0.0), reverse=True)
            top_promo_products = b_prods[:3]
            formatted_promo_brands.append({
                "id": b.id,
                "name": b.name,
                "slug": b.slug,
                "is_featured": b.is_featured,
                "top_promo_products": top_promo_products,
            })

        # 6. Preload Bundling
        bund_stmt = (
            select(ProductBundling)
            .options(
                selectinload(ProductBundling.items).selectinload(ProductBundlingItem.product).selectinload(Product.images),
                selectinload(ProductBundling.items).selectinload(ProductBundlingItem.variant),
            )
            .where(
                ProductBundling.deleted == False,
                or_(ProductBundling.is_active.is_(True), ProductBundling.is_active.is_(None)),
            )
            .order_by(ProductBundling.created_at.desc())
            .limit(8)
        )
        bund_res = await db.execute(bund_stmt)
        bundles = bund_res.scalars().all()
        formatted_bundles = []
        for bundle in bundles:
            total_original = 0.0
            for bi in (bundle.items or []):
                qty = bi.quantity or 1
                if bi.variant and (bi.variant.sell_price or 0) > 0:
                    total_original += float(bi.variant.sell_price) * qty
                elif bi.product and bi.product.variants:
                    valid_v = [v for v in bi.product.variants if not v.deleted and (v.sell_price or 0) > 0]
                    if valid_v:
                        total_original += float(min(v.sell_price for v in valid_v)) * qty

            bundle_price = float(bundle.price or 0.0)
            if total_original <= 0:
                total_original = bundle_price

            discount_percent = 0.0
            if total_original > bundle_price and total_original > 0:
                discount_percent = round(((total_original - bundle_price) / total_original) * 100.0)

            thumb = getattr(bundle, "banner_image", None) or bundle.image_url
            if not thumb and bundle.items and bundle.items[0].product:
                p = bundle.items[0].product
                thumb = p.thumbnail or (p.images[0].image if p.images else None)

            formatted_bundles.append({
                "id": bundle.id,
                "name": bundle.name,
                "slug": bundle.slug,
                "description": bundle.description,
                "price": bundle_price,
                "total_price": bundle_price,
                "total_original": total_original,
                "discount_percent": discount_percent,
                "thumbnail_url": thumb,
                "banner_image": getattr(bundle, "banner_image", None),
                "image_url": bundle.image_url,
                "items": [
                    {
                        "id": bi.id,
                        "product_id": bi.product_id,
                        "variant_id": bi.variant_id,
                        "quantity": bi.quantity,
                        "product_name": bi.product.name if bi.product else None,
                        "variant_name": bi.variant.variant_name if bi.variant else None,
                    }
                    for bi in (bundle.items or [])
                ],
            })

        # 7. Preload Recommended (products not in bestsellers)
        rec_stmt = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.brand),
                selectinload(Product.category),
                selectinload(Product.price_product_settings),
            )
            .where(
                Product.deleted == False,
                or_(Product.status == 1, Product.status.is_(None)),
                Product.id.not_in(bestseller_ids) if bestseller_ids else True,
            )
            .limit(10)
        )
        rec_res = await db.execute(rec_stmt)
        formatted_recommended = [_format_product_card(p) for p in rec_res.scalars().all()]

        # 8. Preload Banners
        ban_stmt = (
            select(Banner)
            .where(Banner.deleted == False, or_(Banner.is_active.is_(True), Banner.is_active.is_(None)))
            .order_by(Banner.sort_order.asc())
        )
        ban_res = await db.execute(ban_stmt)
        formatted_banners = [
            {
                "id": b.id,
                "title": b.title,
                "link_url": b.link_url,
                "image_web_url": b.image_web_url,
                "image_mobile_url": b.image_mobile_url or b.image_web_url,
                "target_type": b.target_type,
                "target_id": b.target_id,
                "type": b.type,
                "sort_order": b.sort_order,
            }
            for b in ban_res.scalars().all()
        ]

        # 9. Preload Events with Popups
        now = datetime.now()
        ev_stmt = (
            select(Event)
            .options(selectinload(Event.popups))
            .where(
                Event.deleted == False,
                or_(Event.is_active.is_(True), Event.is_active.is_(None)),
                or_(Event.start_date.is_(None), Event.start_date <= now),
                or_(Event.end_date.is_(None), Event.end_date >= now),
            )
        )
        ev_res = await db.execute(ev_stmt)
        formatted_events = [
            {
                "id": ev.id,
                "title": ev.title,
                "slug": ev.slug,
                "description": ev.description,
                "banner_image": ev.banner_image,
                "popups": [
                    {
                        "id": pop.id,
                        "title": pop.title,
                        "image_url": pop.image_url,
                        "link_url": pop.link_url,
                        "button_text": pop.button_text,
                    }
                    for pop in (ev.popups or [])
                    if pop.is_active
                ],
            }
            for ev in ev_res.scalars().unique().all()
        ]

        # Helper to map section_key to items
        def _get_items_for_key(sec_key: str, sec_meta: dict[str, Any] | None) -> list[Any]:
            k = sec_key.lower()
            if "kategori" in k or "category" in k:
                return formatted_categories
            elif "best" in k:
                return formatted_bestsellers
            elif "pilihan" in k or ("brand" in k and "promo" not in k) or "merek" in k:
                return formatted_brands
            elif "promo" in k:
                return formatted_promo_brands
            elif "spesial" in k or "special" in k or "sorotan" in k or "featured" in k:
                feat_id = (sec_meta or {}).get("featured_product_id")
                if feat_id:
                    feat = next(
                        (p for p in formatted_bestsellers + formatted_recommended if str(p.get("id")) == str(feat_id)),
                        None,
                    )
                    if feat:
                        return [feat]
                return [formatted_bestsellers[0]] if formatted_bestsellers else (formatted_recommended[:1] if formatted_recommended else [])
            elif "bundl" in k or "paket" in k:
                return formatted_bundles
            elif "rekomendasi" in k or "recommend" in k:
                return formatted_recommended
            elif "banner" in k or "slider" in k or "hero" in k:
                return formatted_banners
            elif "event" in k or "popup" in k:
                return formatted_events
            return []

        # If DB sections exist, use them and attach items
        result_sections = []
        seen_keys = set()
        if db_sections:
            for sec in db_sections:
                k = sec.section_key
                seen_keys.add(k.lower())
                items = _get_items_for_key(k, sec.meta)
                result_sections.append({
                    "id": sec.id,
                    "section_key": sec.section_key,
                    "title": sec.title,
                    "sort_order": sec.sort_order,
                    "is_visible": sec.is_visible,
                    "meta": sec.meta,
                    "items": items,
                })

        # Default fallback sections if not defined in DB
        default_sections = [
            {"section_key": "banners", "title": "Banner Promo", "items": formatted_banners, "sort_order": 1},
            {"section_key": "kategori", "title": "Kategori Pilihan", "items": formatted_categories, "sort_order": 2},
            {"section_key": "best_seller", "title": "Best Seller", "items": formatted_bestsellers, "sort_order": 3},
            {"section_key": "pilihan_brand", "title": "Pilihan Brand", "items": formatted_brands, "sort_order": 4},
            {"section_key": "promo_brand", "title": "Promo Brand", "items": formatted_promo_brands, "sort_order": 5},
            {
                "section_key": "spesial",
                "title": "Produk Spesial",
                "items": [formatted_bestsellers[0]] if formatted_bestsellers else [],
                "sort_order": 6,
            },
            {"section_key": "bundling", "title": "Paket Bundling", "items": formatted_bundles, "sort_order": 7},
            {"section_key": "rekomendasi", "title": "Rekomendasi Untuk Anda", "items": formatted_recommended, "sort_order": 8},
            {"section_key": "events", "title": "Event Popups", "items": formatted_events, "sort_order": 9},
        ]

        if not result_sections:
            result_sections = [
                {
                    "id": str(uuid.uuid4()),
                    "section_key": ds["section_key"],
                    "title": ds["title"],
                    "sort_order": ds["sort_order"],
                    "is_visible": True,
                    "meta": None,
                    "items": ds["items"],
                }
                for ds in default_sections
            ]
        else:
            max_sort = max(s["sort_order"] for s in result_sections) if result_sections else 0
            for ds in default_sections:
                if not any(ds["section_key"] in k for k in seen_keys):
                    max_sort += 1
                    result_sections.append({
                        "id": str(uuid.uuid4()),
                        "section_key": ds["section_key"],
                        "title": ds["title"],
                        "sort_order": max_sort,
                        "is_visible": True,
                        "meta": None,
                        "items": ds["items"],
                    })

        result_sections.sort(key=lambda s: s.get("sort_order", 0))
        return result_sections

    # --- About Us ---
    async def get_about_us_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_about_us.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=AboutUsRead, **filters
        )

    async def get_about_us_by_id(self, db: AsyncSession, item_id: int) -> dict[str, Any]:
        item = await crud_about_us.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"AboutUs record with ID {item_id} not found")
        return item

    async def create_about_us(self, db: AsyncSession, obj_in: AboutUsCreate) -> dict[str, Any]:
        res = await crud_about_us.create(db=db, object=obj_in)
        await db.commit()
        return res

    async def update_about_us(self, db: AsyncSession, item_id: int, obj_in: AboutUsUpdate) -> dict[str, Any]:
        item = await crud_about_us.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"AboutUs record with ID {item_id} not found")
        res = await crud_about_us.update(db=db, object=obj_in, id=item_id)
        await db.commit()
        return res

    async def delete_about_us(self, db: AsyncSession, item_id: int) -> None:
        item = await crud_about_us.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"AboutUs record with ID {item_id} not found")
        await crud_about_us.delete(db=db, id=item_id)
        await db.commit()

    # --- Blog Post ---
    async def get_blog_posts_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_blog_posts.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=BlogPostRead, **filters
        )

    async def get_blog_post_by_id(self, db: AsyncSession, item_id: int) -> dict[str, Any]:
        item = await crud_blog_posts.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"Blog post with ID {item_id} not found")
        return item

    async def create_blog_post(self, db: AsyncSession, obj_in: BlogPostCreate) -> dict[str, Any]:
        existing = await crud_blog_posts.get(db=db, slug=obj_in.slug)
        if existing:
            raise ResourceExistsError(f"Blog post with slug '{obj_in.slug}' already exists")
        res = await crud_blog_posts.create(db=db, object=obj_in)
        await db.commit()
        return res

    async def update_blog_post(self, db: AsyncSession, item_id: int, obj_in: BlogPostUpdate) -> dict[str, Any]:
        item = await crud_blog_posts.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"Blog post with ID {item_id} not found")
        if obj_in.slug and obj_in.slug != item.get("slug"):
            existing = await crud_blog_posts.get(db=db, slug=obj_in.slug)
            if existing:
                raise ResourceExistsError(f"Blog post with slug '{obj_in.slug}' already exists")
        res = await crud_blog_posts.update(db=db, object=obj_in, id=item_id)
        await db.commit()
        return res

    async def delete_blog_post(self, db: AsyncSession, item_id: int) -> None:
        item = await crud_blog_posts.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"Blog post with ID {item_id} not found")
        await crud_blog_posts.delete(db=db, id=item_id)
        await db.commit()

    # --- FAQ ---
    async def get_faqs_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_faqs.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=FaqRead, **filters
        )

    async def get_faq_by_id(self, db: AsyncSession, item_id: int) -> dict[str, Any]:
        item = await crud_faqs.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"FAQ with ID {item_id} not found")
        return item

    async def create_faq(self, db: AsyncSession, obj_in: FaqCreate) -> dict[str, Any]:
        res = await crud_faqs.create(db=db, object=obj_in)
        await db.commit()
        return res

    async def update_faq(self, db: AsyncSession, item_id: int, obj_in: FaqUpdate) -> dict[str, Any]:
        item = await crud_faqs.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"FAQ with ID {item_id} not found")
        res = await crud_faqs.update(db=db, object=obj_in, id=item_id)
        await db.commit()
        return res

    async def delete_faq(self, db: AsyncSession, item_id: int) -> None:
        item = await crud_faqs.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"FAQ with ID {item_id} not found")
        await crud_faqs.delete(db=db, id=item_id)
        await db.commit()

    # --- How To Return ---
    async def get_how_to_returns_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_how_to_returns.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=HowToReturnRead, **filters
        )

    async def get_how_to_return_by_id(self, db: AsyncSession, item_id: int) -> dict[str, Any]:
        item = await crud_how_to_returns.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"HowToReturn record with ID {item_id} not found")
        return item

    async def create_how_to_return(self, db: AsyncSession, obj_in: HowToReturnCreate) -> dict[str, Any]:
        existing = await crud_how_to_returns.get(db=db, slug=obj_in.slug)
        if existing:
            raise ResourceExistsError(f"HowToReturn with slug '{obj_in.slug}' already exists")
        res = await crud_how_to_returns.create(db=db, object=obj_in)
        await db.commit()
        return res

    async def update_how_to_return(self, db: AsyncSession, item_id: int, obj_in: HowToReturnUpdate) -> dict[str, Any]:
        item = await crud_how_to_returns.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"HowToReturn record with ID {item_id} not found")
        if obj_in.slug and obj_in.slug != item.get("slug"):
            existing = await crud_how_to_returns.get(db=db, slug=obj_in.slug)
            if existing:
                raise ResourceExistsError(f"HowToReturn with slug '{obj_in.slug}' already exists")
        res = await crud_how_to_returns.update(db=db, object=obj_in, id=item_id)
        await db.commit()
        return res

    async def delete_how_to_return(self, db: AsyncSession, item_id: int) -> None:
        item = await crud_how_to_returns.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"HowToReturn record with ID {item_id} not found")
        await crud_how_to_returns.delete(db=db, id=item_id)
        await db.commit()

    # --- Privacy Policy ---
    async def get_privacy_policies_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_privacy_policies.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=PrivacyPolicyRead, **filters
        )

    async def get_privacy_policy_by_id(self, db: AsyncSession, item_id: int) -> dict[str, Any]:
        item = await crud_privacy_policies.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"PrivacyPolicy record with ID {item_id} not found")
        return item

    async def create_privacy_policy(self, db: AsyncSession, obj_in: PrivacyPolicyCreate) -> dict[str, Any]:
        existing = await crud_privacy_policies.get(db=db, slug=obj_in.slug)
        if existing:
            raise ResourceExistsError(f"PrivacyPolicy with slug '{obj_in.slug}' already exists")
        res = await crud_privacy_policies.create(db=db, object=obj_in)
        await db.commit()
        return res

    async def update_privacy_policy(self, db: AsyncSession, item_id: int, obj_in: PrivacyPolicyUpdate) -> dict[str, Any]:
        item = await crud_privacy_policies.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"PrivacyPolicy record with ID {item_id} not found")
        if obj_in.slug and obj_in.slug != item.get("slug"):
            existing = await crud_privacy_policies.get(db=db, slug=obj_in.slug)
            if existing:
                raise ResourceExistsError(f"PrivacyPolicy with slug '{obj_in.slug}' already exists")
        res = await crud_privacy_policies.update(db=db, object=obj_in, id=item_id)
        await db.commit()
        return res

    async def delete_privacy_policy(self, db: AsyncSession, item_id: int) -> None:
        item = await crud_privacy_policies.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"PrivacyPolicy record with ID {item_id} not found")
        await crud_privacy_policies.delete(db=db, id=item_id)
        await db.commit()

    # --- Terms and Condition ---
    async def get_terms_and_conditions_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_terms_and_conditions.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=TermsAndConditionRead, **filters
        )

    async def get_terms_and_condition_by_id(self, db: AsyncSession, item_id: int) -> dict[str, Any]:
        item = await crud_terms_and_conditions.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"TermsAndCondition record with ID {item_id} not found")
        return item

    async def create_terms_and_condition(self, db: AsyncSession, obj_in: TermsAndConditionCreate) -> dict[str, Any]:
        existing = await crud_terms_and_conditions.get(db=db, slug=obj_in.slug)
        if existing:
            raise ResourceExistsError(f"TermsAndCondition with slug '{obj_in.slug}' already exists")
        res = await crud_terms_and_conditions.create(db=db, object=obj_in)
        await db.commit()
        return res

    async def update_terms_and_condition(
        self, db: AsyncSession, item_id: int, obj_in: TermsAndConditionUpdate
    ) -> dict[str, Any]:
        item = await crud_terms_and_conditions.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"TermsAndCondition record with ID {item_id} not found")
        if obj_in.slug and obj_in.slug != item.get("slug"):
            existing = await crud_terms_and_conditions.get(db=db, slug=obj_in.slug)
            if existing:
                raise ResourceExistsError(f"TermsAndCondition with slug '{obj_in.slug}' already exists")
        res = await crud_terms_and_conditions.update(db=db, object=obj_in, id=item_id)
        await db.commit()
        return res

    async def delete_terms_and_condition(self, db: AsyncSession, item_id: int) -> None:
        item = await crud_terms_and_conditions.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"TermsAndCondition record with ID {item_id} not found")
        await crud_terms_and_conditions.delete(db=db, id=item_id)
        await db.commit()

    # --- Warranty Claim ---
    async def get_warranty_claims_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_warranty_claims.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=WarrantyClaimRead, **filters
        )

    async def get_warranty_claim_by_id(self, db: AsyncSession, item_id: int) -> dict[str, Any]:
        item = await crud_warranty_claims.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"WarrantyClaim record with ID {item_id} not found")
        return item

    async def create_warranty_claim(self, db: AsyncSession, obj_in: WarrantyClaimCreate) -> dict[str, Any]:
        existing = await crud_warranty_claims.get(db=db, slug=obj_in.slug)
        if existing:
            raise ResourceExistsError(f"WarrantyClaim with slug '{obj_in.slug}' already exists")
        res = await crud_warranty_claims.create(db=db, object=obj_in)
        await db.commit()
        return res

    async def update_warranty_claim(self, db: AsyncSession, item_id: int, obj_in: WarrantyClaimUpdate) -> dict[str, Any]:
        item = await crud_warranty_claims.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"WarrantyClaim record with ID {item_id} not found")
        if obj_in.slug and obj_in.slug != item.get("slug"):
            existing = await crud_warranty_claims.get(db=db, slug=obj_in.slug)
            if existing:
                raise ResourceExistsError(f"WarrantyClaim with slug '{obj_in.slug}' already exists")
        res = await crud_warranty_claims.update(db=db, object=obj_in, id=item_id)
        await db.commit()
        return res

    async def delete_warranty_claim(self, db: AsyncSession, item_id: int) -> None:
        item = await crud_warranty_claims.get(db=db, id=item_id, deleted=False)
        if not item:
            raise ResourceNotFoundError(f"WarrantyClaim record with ID {item_id} not found")
        await crud_warranty_claims.delete(db=db, id=item_id)
        await db.commit()


content_service = ContentService()
