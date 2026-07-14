from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import (
    crud_about_us,
    crud_blog_posts,
    crud_faqs,
    crud_how_to_returns,
    crud_privacy_policies,
    crud_terms_and_conditions,
    crud_warranty_claims,
)
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
    # --- About Us ---
    async def get_about_us_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_about_us.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=AboutUsRead, **filters
        )

    async def get_about_us_by_id(self, db: AsyncSession, item_id: int) -> dict[str, Any]:
        item = await crud_about_us.get(db=db, id=item_id, is_deleted=False)
        if not item:
            raise ResourceNotFoundError(f"AboutUs record with ID {item_id} not found")
        return item

    async def create_about_us(self, db: AsyncSession, obj_in: AboutUsCreate) -> dict[str, Any]:
        res = await crud_about_us.create(db=db, object=obj_in)
        await db.commit()
        return res

    async def update_about_us(self, db: AsyncSession, item_id: int, obj_in: AboutUsUpdate) -> dict[str, Any]:
        item = await crud_about_us.get(db=db, id=item_id, is_deleted=False)
        if not item:
            raise ResourceNotFoundError(f"AboutUs record with ID {item_id} not found")
        res = await crud_about_us.update(db=db, object=obj_in, id=item_id)
        await db.commit()
        return res

    async def delete_about_us(self, db: AsyncSession, item_id: int) -> None:
        item = await crud_about_us.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_blog_posts.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_blog_posts.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_blog_posts.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_faqs.get(db=db, id=item_id, is_deleted=False)
        if not item:
            raise ResourceNotFoundError(f"FAQ with ID {item_id} not found")
        return item

    async def create_faq(self, db: AsyncSession, obj_in: FaqCreate) -> dict[str, Any]:
        res = await crud_faqs.create(db=db, object=obj_in)
        await db.commit()
        return res

    async def update_faq(self, db: AsyncSession, item_id: int, obj_in: FaqUpdate) -> dict[str, Any]:
        item = await crud_faqs.get(db=db, id=item_id, is_deleted=False)
        if not item:
            raise ResourceNotFoundError(f"FAQ with ID {item_id} not found")
        res = await crud_faqs.update(db=db, object=obj_in, id=item_id)
        await db.commit()
        return res

    async def delete_faq(self, db: AsyncSession, item_id: int) -> None:
        item = await crud_faqs.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_how_to_returns.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_how_to_returns.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_how_to_returns.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_privacy_policies.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_privacy_policies.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_privacy_policies.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_terms_and_conditions.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_terms_and_conditions.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_terms_and_conditions.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_warranty_claims.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_warranty_claims.get(db=db, id=item_id, is_deleted=False)
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
        item = await crud_warranty_claims.get(db=db, id=item_id, is_deleted=False)
        if not item:
            raise ResourceNotFoundError(f"WarrantyClaim record with ID {item_id} not found")
        await crud_warranty_claims.delete(db=db, id=item_id)
        await db.commit()


content_service = ContentService()
