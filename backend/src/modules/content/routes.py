from typing import Annotated, Any
from fastapi import APIRouter, Depends
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep
from ...modules.rbac.dependencies import require_permission
from ..common.utils.error_handler import handle_exception
from .dependencies import ContentServiceDep
from .schemas import AboutUsCreate, AboutUsRead, AboutUsUpdate, BlogPostCreate, BlogPostRead, BlogPostUpdate, FaqCreate, FaqRead, FaqUpdate, HowToReturnCreate, HowToReturnRead, HowToReturnUpdate, PrivacyPolicyCreate, PrivacyPolicyRead, PrivacyPolicyUpdate, TermsAndConditionCreate, TermsAndConditionRead, TermsAndConditionUpdate, WarrantyClaimCreate, WarrantyClaimRead, WarrantyClaimUpdate
router = APIRouter()

@router.get('/about-us/', response_model=PaginatedListResponse[AboutUsRead], summary='List About Us records', tags=['Content: About Us'])
async def list_about_us(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await service.get_about_us_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/about-us/{item_id}', response_model=AboutUsRead, summary='Get About Us record', tags=['Content: About Us'])
async def get_about_us(item_id: int, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep) -> dict[str, Any]:
    return await service.get_about_us_by_id(db, item_id)

@router.get('/blog-posts/', response_model=PaginatedListResponse[BlogPostRead], summary='List Blog Posts', tags=['Content: Blog'])
async def list_blog_posts(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await service.get_blog_posts_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/blog-posts/{item_id}', response_model=BlogPostRead, summary='Get Blog Post', tags=['Content: Blog'])
async def get_blog_post(item_id: int, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep) -> dict[str, Any]:
    return await service.get_blog_post_by_id(db, item_id)

@router.get('/faqs/', response_model=PaginatedListResponse[FaqRead], summary='List FAQs', tags=['Content: FAQ'])
async def list_faqs(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await service.get_faqs_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/faqs/{item_id}', response_model=FaqRead, summary='Get FAQ', tags=['Content: FAQ'])
async def get_faq(item_id: int, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep) -> dict[str, Any]:
    return await service.get_faq_by_id(db, item_id)

@router.get('/how-to-returns/', response_model=PaginatedListResponse[HowToReturnRead], summary='List How To Returns', tags=['Content: How To Return'])
async def list_how_to_returns(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await service.get_how_to_returns_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/how-to-returns/{item_id}', response_model=HowToReturnRead, summary='Get How To Return record', tags=['Content: How To Return'])
async def get_how_to_return(item_id: int, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep) -> dict[str, Any]:
    return await service.get_how_to_return_by_id(db, item_id)

@router.get('/privacy-policies/', response_model=PaginatedListResponse[PrivacyPolicyRead], summary='List Privacy Policies', tags=['Content: Privacy Policy'])
async def list_privacy_policies(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await service.get_privacy_policies_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/privacy-policies/{item_id}', response_model=PrivacyPolicyRead, summary='Get Privacy Policy record', tags=['Content: Privacy Policy'])
async def get_privacy_policy(item_id: int, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep) -> dict[str, Any]:
    return await service.get_privacy_policy_by_id(db, item_id)

@router.get('/terms-and-conditions/', response_model=PaginatedListResponse[TermsAndConditionRead], summary='List Terms and Conditions', tags=['Content: Terms and Condition'])
async def list_terms_and_conditions(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await service.get_terms_and_conditions_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/terms-and-conditions/{item_id}', response_model=TermsAndConditionRead, summary='Get Terms and Condition record', tags=['Content: Terms and Condition'])
async def get_terms_and_condition(item_id: int, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep) -> dict[str, Any]:
    return await service.get_terms_and_condition_by_id(db, item_id)

@router.get('/warranty-claims/', response_model=PaginatedListResponse[WarrantyClaimRead], summary='List Warranty Claims', tags=['Content: Warranty Claim'])
async def list_warranty_claims(db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep, page: int=1, items_per_page: int=10) -> dict[str, Any]:
    data = await service.get_warranty_claims_paginated(db=db, skip=compute_offset(page, items_per_page), limit=items_per_page)
    return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)

@router.get('/warranty-claims/{item_id}', response_model=WarrantyClaimRead, summary='Get Warranty Claim record', tags=['Content: Warranty Claim'])
async def get_warranty_claim(item_id: int, db: AsyncSessionDep, _: Annotated[dict[str, Any], Depends(require_permission('content:read'))], service: ContentServiceDep) -> dict[str, Any]:
    return await service.get_warranty_claim_by_id(db, item_id)
from sqlalchemy import select
from .models import Banner, HomepageSection, Event, Notification

@router.get('/banners', summary='Get Active Banners', description='Get active banners for mobile app')
async def get_banners(db: AsyncSessionDep):
    stmt = select(Banner).where(Banner.deleted == False, Banner.is_active == True).order_by(Banner.sort_order.asc())
    result = await db.execute(stmt)
    return {'success': True, 'data': result.scalars().all()}

@router.get('/homepages', summary='Get Homepage Layout', description='Get active homepage layout config')
async def get_homepage_sections(db: AsyncSessionDep):
    stmt = select(HomepageSection).where(HomepageSection.is_visible == True).order_by(HomepageSection.sort_order.asc())
    result = await db.execute(stmt)
    return {'success': True, 'data': result.scalars().all()}

@router.get('/events/active', summary='Get Active Events', description='Get active events with their popups')
async def get_active_events(db: AsyncSessionDep):
    from datetime import datetime
    now = datetime.now()
    stmt = select(Event).where(Event.deleted == False, Event.is_active == True, Event.start_date <= now, Event.end_date >= now)
    result = await db.execute(stmt)
    return {'success': True, 'data': result.scalars().unique().all()}

@router.get('/notifications', summary='Get Broadcast Notifications', description='Get latest notifications')
async def get_notifications(db: AsyncSessionDep):
    stmt = select(Notification).where(Notification.is_broadcast == True).order_by(Notification.created_at.desc()).limit(20)
    result = await db.execute(stmt)
    return {'success': True, 'data': result.scalars().all()}