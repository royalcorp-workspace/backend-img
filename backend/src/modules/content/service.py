import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.logging import get_logger
from ..category.models import Category
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from ..common.utils import get_media_url
from ..product.models import (
    Brand,
    PriceProductSetting,
    Product,
    ProductBundling,
    ProductBundlingItem,
    ProductImage,
    ProductVariant,
)
from ..review.models import Review
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

        # Condition to ensure products have valid in-stock variants with price
        has_stock_and_price = Product.variants.any(
            and_(
                ProductVariant.deleted == False,
                ProductVariant.sell_price > 0,
                ProductVariant.stock_qty > 0,
            )
        )

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
                or_(Product.show_on_web == True, Product.show_on_web.is_(None)),
                Product.best_seller == True,
                has_stock_and_price,
            )
            .limit(10)
        )
        bs_res = await db.execute(bs_stmt)
        bestseller_products = bs_res.scalars().all()
        bestseller_ids = [p.id for p in bestseller_products]

        # Preload review counts for all products
        rev_count_stmt = (
            select(Review.product_id, func.count(Review.id).label("cnt"))
            .where(
                or_(Review.is_deleted == False, Review.is_deleted.is_(None)),
                Review.is_published == True,
            )
            .group_by(Review.product_id)
        )
        rev_count_res = await db.execute(rev_count_stmt)
        review_counts_map = {row[0]: int(row[1] or 0) for row in rev_count_res.all()}

        def _format_product_card(prod: Product, explicit_review_count: int | None = None) -> dict[str, Any] | None:
            # Prioritize variants with price and stock
            valid_variants = [
                v for v in (prod.variants or [])
                if not v.deleted and (v.sell_price or 0) > 0 and (v.stock_qty or 0) > 0
            ]
            if not valid_variants:
                valid_variants = [v for v in (prod.variants or []) if not v.deleted and (v.sell_price or 0) > 0]

            if valid_variants:
                sorted_vars = sorted(
                    valid_variants,
                    key=lambda v: (float(v.sell_price or 0.0), getattr(v, "created_at", None) or datetime.min),
                    reverse=True,
                )
                chosen_v = sorted_vars[0]
                s_price = float(chosen_v.sell_price or 0.0)
                b_price = float(chosen_v.base_price or 0.0)
                if b_price <= 0 or b_price < s_price:
                    b_price = s_price
            else:
                s_price = float(getattr(prod, "sell_price", 0.0) or 0.0)
                b_price = float(getattr(prod, "base_price", 0.0) or s_price) or s_price

            if s_price <= 0:
                return None

            disc_percent = 0.0
            if b_price > s_price and b_price > 0:
                disc_percent = round(((b_price - s_price) / b_price) * 100.0, 1)
                if disc_percent.is_integer():
                    disc_percent = int(disc_percent)
            elif prod.price_product_settings:
                for pps in prod.price_product_settings:
                    if getattr(pps, "is_active", True):
                        val = float(pps.discount_value or 0.0)
                        dtype = pps.discount_type
                        if dtype == 1 or (0 < val <= 100 and dtype != 2):
                            disc_percent = round(val, 1)
                            if disc_percent.is_integer():
                                disc_percent = int(disc_percent)
                            s_price = round(b_price * (1.0 - val / 100.0), 2)
                        elif val > 0 and b_price > 0:
                            s_price = max(0.0, b_price - val)
                            disc_percent = round((val / b_price) * 100.0, 1)
                            if disc_percent.is_integer():
                                disc_percent = int(disc_percent)
                        break

            thumb = get_media_url(prod.thumbnail)
            if not thumb and prod.images:
                for img in prod.images:
                    t = get_media_url(img.image)
                    if t:
                        thumb = t
                        break
            if not thumb and prod.variants:
                for v in prod.variants:
                    v_img = getattr(v, "image_url", None)
                    if v_img:
                        thumb = get_media_url(v_img)
                        if thumb:
                            break

            r_count = explicit_review_count if explicit_review_count is not None else review_counts_map.get(prod.id, 0)

            return {
                "id": prod.id,
                "title": prod.name,
                "name": prod.name,
                "slug": prod.slug,
                "image": thumb,
                "thumbnail": thumb,
                "thumbnail_url": thumb,
                "base_price": b_price,
                "sell_price": s_price,
                "discount_percent": disc_percent,
                "counting_review": r_count,
                "reviews_count": r_count,
                "review_count": r_count,
            }

        formatted_bestsellers = [c for p in bestseller_products if (c := _format_product_card(p)) is not None]

        # 3. Preload Newest Products (10 products with stock & price)
        new_stmt = (
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
                or_(Product.show_on_web == True, Product.show_on_web.is_(None)),
                has_stock_and_price,
            )
            .order_by(Product.created_at.desc())
            .limit(10)
        )
        new_res = await db.execute(new_stmt)
        formatted_newest = [c for p in new_res.scalars().all() if (c := _format_product_card(p)) is not None]

        # 4. Preload Cheapest Products (10 products ordered by min variant sell_price asc, with stock)
        cheapest_subq = (
            select(
                ProductVariant.product_id,
                func.min(ProductVariant.sell_price).label("min_sell_price"),
            )
            .where(
                ProductVariant.deleted == False,
                ProductVariant.sell_price > 0,
                ProductVariant.stock_qty > 0,
            )
            .group_by(ProductVariant.product_id)
            .subquery()
        )
        cheap_stmt = (
            select(Product)
            .join(cheapest_subq, Product.id == cheapest_subq.c.product_id)
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
                or_(Product.show_on_web == True, Product.show_on_web.is_(None)),
            )
            .order_by(cheapest_subq.c.min_sell_price.asc())
            .limit(10)
        )
        cheap_res = await db.execute(cheap_stmt)
        formatted_cheapest = [c for p in cheap_res.scalars().all() if (c := _format_product_card(p)) is not None]

        # 5. Preload Top Reviews (products with stock, price, and review counts)
        top_reviews_stmt = (
            select(Product, func.count(Review.id).label("reviews_count"))
            .outerjoin(
                Review,
                (Review.product_id == Product.id)
                & or_(Review.is_deleted == False, Review.is_deleted.is_(None))
                & (Review.is_published == True),
            )
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
                or_(Product.show_on_web == True, Product.show_on_web.is_(None)),
                has_stock_and_price,
            )
            .group_by(Product.id)
            .order_by(func.count(Review.id).desc(), Product.created_at.desc())
            .limit(10)
        )
        top_reviews_res = await db.execute(top_reviews_stmt)
        formatted_top_reviews = []
        for row in top_reviews_res.all():
            prod = row[0]
            r_count = int(row[1] or 0)
            card = _format_product_card(prod, explicit_review_count=r_count)
            if card is not None:
                formatted_top_reviews.append(card)

        # 7. Preload Bundling
        bund_stmt = (
            select(ProductBundling)
            .options(
                selectinload(ProductBundling.items).selectinload(ProductBundlingItem.product).selectinload(Product.images),
                selectinload(ProductBundling.items).selectinload(ProductBundlingItem.variant),
            )
            .where(
                ProductBundling.deleted == False,
                or_(ProductBundling.is_active.is_(True), ProductBundling.is_active.is_(None)),
                ProductBundling.price > 0,
            )
            .order_by(ProductBundling.created_at.desc())
            .limit(8)
        )
        bund_res = await db.execute(bund_stmt)
        bundles = bund_res.scalars().all()
        formatted_bundles = []
        for bundle in bundles:
            bundle_price = float(bundle.price or 0.0)
            if bundle_price <= 0:
                continue

            total_original = 0.0
            for bi in (bundle.items or []):
                qty = bi.quantity or 1
                if bi.variant and (bi.variant.sell_price or 0) > 0:
                    total_original += float(bi.variant.sell_price) * qty
                elif bi.product and bi.product.variants:
                    valid_v = [v for v in bi.product.variants if not v.deleted and (v.sell_price or 0) > 0]
                    if valid_v:
                        total_original += float(min(v.sell_price for v in valid_v)) * qty

            if total_original <= 0 or total_original < bundle_price:
                total_original = bundle_price

            discount_percent = 0.0
            if total_original > bundle_price and total_original > 0:
                discount_percent = round(((total_original - bundle_price) / total_original) * 100.0, 1)
                if discount_percent.is_integer():
                    discount_percent = int(discount_percent)

            thumb = get_media_url(getattr(bundle, "banner_image", None) or bundle.image_url)
            if not thumb and bundle.items and bundle.items[0].product:
                p = bundle.items[0].product
                thumb = get_media_url(p.thumbnail or (p.images[0].image if p.images else None))

            formatted_bundles.append({
                "id": bundle.id,
                "title": bundle.name,
                "name": bundle.name,
                "slug": bundle.slug,
                "image": thumb,
                "thumbnail": thumb,
                "thumbnail_url": thumb,
                "base_price": total_original,
                "sell_price": bundle_price,
                "discount_percent": discount_percent,
                "counting_review": 0,
                "reviews_count": 0,
                "review_count": 0,
            })

        # 8. Preload Recommended (in-stock products not in bestsellers, fallback to all in-stock)
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
                or_(Product.show_on_web == True, Product.show_on_web.is_(None)),
                has_stock_and_price,
                Product.id.not_in(bestseller_ids) if bestseller_ids else True,
            )
            .limit(10)
        )
        rec_res = await db.execute(rec_stmt)
        rec_products = rec_res.scalars().all()
        if not rec_products:
            rec_fallback_stmt = (
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
                    or_(Product.show_on_web == True, Product.show_on_web.is_(None)),
                    has_stock_and_price,
                )
                .order_by(Product.name.asc())
                .limit(10)
            )
            rec_fallback_res = await db.execute(rec_fallback_stmt)
            rec_products = rec_fallback_res.scalars().all()

        formatted_recommended = [c for p in rec_products if (c := _format_product_card(p)) is not None]

        # Helper to map section_key to items
        def _get_items_for_key(sec_key: str, sec_meta: dict[str, Any] | None) -> list[Any]:
            k = sec_key.lower()
            if any(x in k for x in ["kategori", "category", "banner", "slider", "hero", "event", "popup"]):
                return []
            elif "best" in k:
                return formatted_bestsellers
            elif "terbaru" in k or "new" in k:
                return formatted_newest
            elif "termurah" in k or "cheap" in k or "murah" in k:
                return formatted_cheapest
            elif "pilihan" in k or ("brand" in k and "promo" not in k) or "merek" in k:
                return formatted_newest
            elif any(x in k for x in ["promo", "review", "ulasan", "top_review"]):
                return formatted_top_reviews
            elif "spesial" in k or "special" in k or "sorotan" in k or "featured" in k:
                feat_id = (sec_meta or {}).get("featured_product_id")
                if feat_id:
                    feat = next(
                        (p for p in formatted_bestsellers + formatted_newest + formatted_recommended if str(p.get("id")) == str(feat_id)),
                        None,
                    )
                    if feat:
                        return [feat]
                return [formatted_bestsellers[0]] if formatted_bestsellers else (formatted_newest[:1] if formatted_newest else (formatted_recommended[:1] if formatted_recommended else []))
            elif "bundl" in k or "paket" in k:
                return formatted_bundles
            elif "rekomendasi" in k or "recommend" in k:
                return formatted_recommended
            return []

        # If DB sections exist, use them and attach items (only product sections)
        result_sections = []
        seen_keys = set()
        if db_sections:
            for sec in db_sections:
                k = sec.section_key.lower()
                # Skip non-product sections completely
                if any(x in k for x in ["kategori", "category", "banner", "slider", "hero", "event", "popup"]):
                    continue

                # If pilihan_brand, convert to product_terbaru
                if "pilihan" in k or ("brand" in k and "promo" not in k) or "merek" in k or "terbaru" in k or "new" in k:
                    target_key = "product_terbaru"
                    target_title = "Produk Terbaru"
                    items = formatted_newest
                elif "termurah" in k or "cheap" in k or "murah" in k:
                    target_key = "product_termurah"
                    target_title = "Produk Termurah"
                    items = formatted_cheapest
                elif any(x in k for x in ["promo", "review", "ulasan", "top_review"]):
                    target_key = "top_reviews"
                    target_title = "Ulasan Terbanyak"
                    items = formatted_top_reviews
                else:
                    target_key = sec.section_key
                    target_title = sec.title
                    items = _get_items_for_key(sec.section_key, sec.meta)

                if not items:
                    continue
                if target_key in seen_keys:
                    continue
                seen_keys.add(target_key)
                result_sections.append({
                    "id": sec.id,
                    "section_key": target_key,
                    "title": target_title,
                    "sort_order": sec.sort_order,
                    "is_visible": sec.is_visible,
                    "meta": sec.meta,
                    "items": items,
                })

        # Default fallback sections (all product-based)
        default_sections = [
            {"section_key": "best_seller", "title": "Produk Unggulan", "items": formatted_bestsellers, "sort_order": 1},
            {"section_key": "product_terbaru", "title": "Produk Terbaru", "items": formatted_newest, "sort_order": 2},
            {"section_key": "product_termurah", "title": "Produk Termurah", "items": formatted_cheapest, "sort_order": 3},
            {"section_key": "top_reviews", "title": "Ulasan Terbanyak", "items": formatted_top_reviews, "sort_order": 4},
            {
                "section_key": "spesial",
                "title": "Produk Spesial",
                "items": [formatted_bestsellers[0]] if formatted_bestsellers else (formatted_newest[:1] if formatted_newest else []),
                "sort_order": 5,
            },
            {"section_key": "bundling", "title": "Paket Spesial / Bundling", "items": formatted_bundles, "sort_order": 6},
            {"section_key": "rekomendasi", "title": "Rekomendasi Produk", "items": formatted_recommended, "sort_order": 7},
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
                if ds["items"]
            ]
        else:
            max_sort = max(s["sort_order"] for s in result_sections) if result_sections else 0
            for ds in default_sections:
                if not ds["items"]:
                    continue
                if ds["section_key"] not in seen_keys:
                    max_sort += 1
                    seen_keys.add(ds["section_key"])
                    result_sections.append({
                        "id": str(uuid.uuid4()),
                        "section_key": ds["section_key"],
                        "title": ds["title"],
                        "sort_order": max_sort,
                        "is_visible": True,
                        "meta": None,
                        "items": ds["items"],
                    })

        # Ensure only sections with items and strictly containing products are returned
        excluded_keys = ["kategori", "category", "banner", "slider", "hero", "event", "popup", "pilihan_brand"]
        result_sections = [
            s for s in result_sections
            if s.get("items") and not any(ex in s.get("section_key", "").lower() for ex in excluded_keys)
        ]
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
