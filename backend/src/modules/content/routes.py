from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import ContentServiceDep
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

router = APIRouter()


# ==========================================
# 1. ABOUT US
# ==========================================
@router.get(
    "/about-us/",
    response_model=PaginatedListResponse[AboutUsRead],
    summary="List About Us records",
    tags=["Content: About Us"],
)
async def list_about_us(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await service.get_about_us_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/about-us/{item_id}",
    response_model=AboutUsRead,
    summary="Get About Us record",
    tags=["Content: About Us"],
)
async def get_about_us(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    return await service.get_about_us_by_id(db, item_id)


@router.post(
    "/about-us/",
    response_model=AboutUsRead,
    status_code=201,
    summary="Create About Us record",
    tags=["Content: About Us"],
)
async def create_about_us(
    obj_in: AboutUsCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:create"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.create_about_us(db, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/about-us/{item_id}",
    response_model=AboutUsRead,
    summary="Update About Us record",
    tags=["Content: About Us"],
)
async def update_about_us(
    item_id: int,
    obj_in: AboutUsUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:update"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.update_about_us(db, item_id, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/about-us/{item_id}",
    status_code=204,
    summary="Delete About Us record",
    tags=["Content: About Us"],
)
async def delete_about_us(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:delete"))],
    service: ContentServiceDep,
) -> None:
    await service.delete_about_us(db, item_id)


# ==========================================
# 2. BLOG POSTS
# ==========================================
@router.get(
    "/blog-posts/",
    response_model=PaginatedListResponse[BlogPostRead],
    summary="List Blog Posts",
    tags=["Content: Blog"],
)
async def list_blog_posts(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await service.get_blog_posts_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/blog-posts/{item_id}",
    response_model=BlogPostRead,
    summary="Get Blog Post",
    tags=["Content: Blog"],
)
async def get_blog_post(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    return await service.get_blog_post_by_id(db, item_id)


@router.post(
    "/blog-posts/",
    response_model=BlogPostRead,
    status_code=201,
    summary="Create Blog Post",
    tags=["Content: Blog"],
)
async def create_blog_post(
    obj_in: BlogPostCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:create"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.create_blog_post(db, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/blog-posts/{item_id}",
    response_model=BlogPostRead,
    summary="Update Blog Post",
    tags=["Content: Blog"],
)
async def update_blog_post(
    item_id: int,
    obj_in: BlogPostUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:update"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.update_blog_post(db, item_id, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/blog-posts/{item_id}",
    status_code=204,
    summary="Delete Blog Post",
    tags=["Content: Blog"],
)
async def delete_blog_post(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:delete"))],
    service: ContentServiceDep,
) -> None:
    await service.delete_blog_post(db, item_id)


# ==========================================
# 3. FAQS
# ==========================================
@router.get(
    "/faqs/",
    response_model=PaginatedListResponse[FaqRead],
    summary="List FAQs",
    tags=["Content: FAQ"],
)
async def list_faqs(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await service.get_faqs_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/faqs/{item_id}",
    response_model=FaqRead,
    summary="Get FAQ",
    tags=["Content: FAQ"],
)
async def get_faq(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    return await service.get_faq_by_id(db, item_id)


@router.post(
    "/faqs/",
    response_model=FaqRead,
    status_code=201,
    summary="Create FAQ",
    tags=["Content: FAQ"],
)
async def create_faq(
    obj_in: FaqCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:create"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.create_faq(db, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/faqs/{item_id}",
    response_model=FaqRead,
    summary="Update FAQ",
    tags=["Content: FAQ"],
)
async def update_faq(
    item_id: int,
    obj_in: FaqUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:update"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.update_faq(db, item_id, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/faqs/{item_id}",
    status_code=204,
    summary="Delete FAQ",
    tags=["Content: FAQ"],
)
async def delete_faq(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:delete"))],
    service: ContentServiceDep,
) -> None:
    await service.delete_faq(db, item_id)


# ==========================================
# 4. HOW TO RETURNS
# ==========================================
@router.get(
    "/how-to-returns/",
    response_model=PaginatedListResponse[HowToReturnRead],
    summary="List How To Returns",
    tags=["Content: How To Return"],
)
async def list_how_to_returns(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await service.get_how_to_returns_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/how-to-returns/{item_id}",
    response_model=HowToReturnRead,
    summary="Get How To Return record",
    tags=["Content: How To Return"],
)
async def get_how_to_return(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    return await service.get_how_to_return_by_id(db, item_id)


@router.post(
    "/how-to-returns/",
    response_model=HowToReturnRead,
    status_code=201,
    summary="Create How To Return record",
    tags=["Content: How To Return"],
)
async def create_how_to_return(
    obj_in: HowToReturnCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:create"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.create_how_to_return(db, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/how-to-returns/{item_id}",
    response_model=HowToReturnRead,
    summary="Update How To Return record",
    tags=["Content: How To Return"],
)
async def update_how_to_return(
    item_id: int,
    obj_in: HowToReturnUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:update"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.update_how_to_return(db, item_id, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/how-to-returns/{item_id}",
    status_code=204,
    summary="Delete How To Return record",
    tags=["Content: How To Return"],
)
async def delete_how_to_return(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:delete"))],
    service: ContentServiceDep,
) -> None:
    await service.delete_how_to_return(db, item_id)


# ==========================================
# 5. PRIVACY POLICIES
# ==========================================
@router.get(
    "/privacy-policies/",
    response_model=PaginatedListResponse[PrivacyPolicyRead],
    summary="List Privacy Policies",
    tags=["Content: Privacy Policy"],
)
async def list_privacy_policies(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await service.get_privacy_policies_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/privacy-policies/{item_id}",
    response_model=PrivacyPolicyRead,
    summary="Get Privacy Policy record",
    tags=["Content: Privacy Policy"],
)
async def get_privacy_policy(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    return await service.get_privacy_policy_by_id(db, item_id)


@router.post(
    "/privacy-policies/",
    response_model=PrivacyPolicyRead,
    status_code=201,
    summary="Create Privacy Policy record",
    tags=["Content: Privacy Policy"],
)
async def create_privacy_policy(
    obj_in: PrivacyPolicyCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:create"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.create_privacy_policy(db, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/privacy-policies/{item_id}",
    response_model=PrivacyPolicyRead,
    summary="Update Privacy Policy record",
    tags=["Content: Privacy Policy"],
)
async def update_privacy_policy(
    item_id: int,
    obj_in: PrivacyPolicyUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:update"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.update_privacy_policy(db, item_id, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/privacy-policies/{item_id}",
    status_code=204,
    summary="Delete Privacy Policy record",
    tags=["Content: Privacy Policy"],
)
async def delete_privacy_policy(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:delete"))],
    service: ContentServiceDep,
) -> None:
    await service.delete_privacy_policy(db, item_id)


# ==========================================
# 6. TERMS AND CONDITIONS
# ==========================================
@router.get(
    "/terms-and-conditions/",
    response_model=PaginatedListResponse[TermsAndConditionRead],
    summary="List Terms and Conditions",
    tags=["Content: Terms and Condition"],
)
async def list_terms_and_conditions(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await service.get_terms_and_conditions_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/terms-and-conditions/{item_id}",
    response_model=TermsAndConditionRead,
    summary="Get Terms and Condition record",
    tags=["Content: Terms and Condition"],
)
async def get_terms_and_condition(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    return await service.get_terms_and_condition_by_id(db, item_id)


@router.post(
    "/terms-and-conditions/",
    response_model=TermsAndConditionRead,
    status_code=201,
    summary="Create Terms and Condition record",
    tags=["Content: Terms and Condition"],
)
async def create_terms_and_condition(
    obj_in: TermsAndConditionCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:create"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.create_terms_and_condition(db, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/terms-and-conditions/{item_id}",
    response_model=TermsAndConditionRead,
    summary="Update Terms and Condition record",
    tags=["Content: Terms and Condition"],
)
async def update_terms_and_condition(
    item_id: int,
    obj_in: TermsAndConditionUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:update"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.update_terms_and_condition(db, item_id, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/terms-and-conditions/{item_id}",
    status_code=204,
    summary="Delete Terms and Condition record",
    tags=["Content: Terms and Condition"],
)
async def delete_terms_and_condition(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:delete"))],
    service: ContentServiceDep,
) -> None:
    await service.delete_terms_and_condition(db, item_id)


# ==========================================
# 7. WARRANTY CLAIMS
# ==========================================
@router.get(
    "/warranty-claims/",
    response_model=PaginatedListResponse[WarrantyClaimRead],
    summary="List Warranty Claims",
    tags=["Content: Warranty Claim"],
)
async def list_warranty_claims(
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    data = await service.get_warranty_claims_paginated(
        db=db, skip=compute_offset(page, items_per_page), limit=items_per_page
    )
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)


@router.get(
    "/warranty-claims/{item_id}",
    response_model=WarrantyClaimRead,
    summary="Get Warranty Claim record",
    tags=["Content: Warranty Claim"],
)
async def get_warranty_claim(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:read"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    return await service.get_warranty_claim_by_id(db, item_id)


@router.post(
    "/warranty-claims/",
    response_model=WarrantyClaimRead,
    status_code=201,
    summary="Create Warranty Claim record",
    tags=["Content: Warranty Claim"],
)
async def create_warranty_claim(
    obj_in: WarrantyClaimCreate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:create"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.create_warranty_claim(db, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.put(
    "/warranty-claims/{item_id}",
    response_model=WarrantyClaimRead,
    summary="Update Warranty Claim record",
    tags=["Content: Warranty Claim"],
)
async def update_warranty_claim(
    item_id: int,
    obj_in: WarrantyClaimUpdate,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:update"))],
    service: ContentServiceDep,
) -> dict[str, Any]:
    try:
        return await service.update_warranty_claim(db, item_id, obj_in)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.delete(
    "/warranty-claims/{item_id}",
    status_code=204,
    summary="Delete Warranty Claim record",
    tags=["Content: Warranty Claim"],
)
async def delete_warranty_claim(
    item_id: int,
    db: AsyncSessionDep,
    _: Annotated[dict[str, Any], Depends(require_permission("content:delete"))],
    service: ContentServiceDep,
) -> None:
    await service.delete_warranty_claim(db, item_id)

from sqlalchemy import select
from .models import Banner, HomepageSection, Event, Notification

# ==========================================
# 8. BANNERS
# ==========================================
@router.get("/banners", summary="Get Active Banners", description="Get active banners for mobile app")
async def get_banners(db: AsyncSessionDep):
    stmt = select(Banner).where(Banner.deleted == False, Banner.is_active == True).order_by(Banner.sort_order.asc())
    result = await db.execute(stmt)
    return {"success": True, "data": result.scalars().all()}

# ==========================================
# 9. HOMEPAGE SECTIONS
# ==========================================
@router.get("/homepages", summary="Get Homepage Layout", description="Get active homepage layout config")
async def get_homepage_sections(db: AsyncSessionDep):
    stmt = select(HomepageSection).where(HomepageSection.is_visible == True).order_by(HomepageSection.sort_order.asc())
    result = await db.execute(stmt)
    return {"success": True, "data": result.scalars().all()}

# ==========================================
# 10. EVENTS & POPUPS
# ==========================================
@router.get("/events/active", summary="Get Active Events", description="Get active events with their popups")
async def get_active_events(db: AsyncSessionDep):
    from datetime import datetime
    now = datetime.now()
    stmt = select(Event).where(
        Event.deleted == False, 
        Event.is_active == True,
        Event.start_date <= now,
        Event.end_date >= now
    )
    result = await db.execute(stmt)
    return {"success": True, "data": result.scalars().unique().all()}

# ==========================================
# 11. NOTIFICATIONS
# ==========================================
@router.get("/notifications", summary="Get Broadcast Notifications", description="Get latest notifications")
async def get_notifications(db: AsyncSessionDep):
    stmt = select(Notification).where(Notification.is_broadcast == True).order_by(Notification.created_at.desc()).limit(20)
    result = await db.execute(stmt)
    return {"success": True, "data": result.scalars().all()}
