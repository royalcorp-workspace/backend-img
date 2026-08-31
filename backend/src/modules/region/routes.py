from typing import Any
import uuid as uuid_pkg
from fastapi import APIRouter
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from ...infrastructure.dependencies import AsyncSessionDep
from .crud import crud_provinces, crud_cities, crud_sub_districts
from .schemas import ProvinceRead, CityRead, SubDistrictRead

router = APIRouter(tags=["Regions"])

@router.get("/provinces", response_model=PaginatedListResponse[ProvinceRead])
async def list_provinces(
    db: AsyncSessionDep,
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    skip = compute_offset(page, items_per_page)
    response = await crud_provinces.get_multi(
        db,
        offset=skip,
        limit=items_per_page,
        deleted=False,
    )
    return paginated_response(crud_data=response, page=page, items_per_page=items_per_page)

@router.get("/provinces/{province_id}", response_model=ProvinceRead)
async def get_province(
    province_id: uuid_pkg.UUID,
    db: AsyncSessionDep,
) -> Any:
    return await crud_provinces.get(db, id=province_id, deleted=False)

@router.get("/cities", response_model=PaginatedListResponse[CityRead])
async def list_cities(
    db: AsyncSessionDep,
    page: int = 1,
    items_per_page: int = 10,
    province_id: str | None = None,
) -> dict[str, Any]:
    skip = compute_offset(page, items_per_page)
    kwargs = {"deleted": False}
    if province_id:
        kwargs["province_id"] = province_id
    response = await crud_cities.get_multi(
        db,
        offset=skip,
        limit=items_per_page,
        **kwargs
    )
    return paginated_response(crud_data=response, page=page, items_per_page=items_per_page)

@router.get("/cities/{city_id}", response_model=CityRead)
async def get_city(
    city_id: uuid_pkg.UUID,
    db: AsyncSessionDep,
) -> Any:
    return await crud_cities.get(db, id=city_id, deleted=False)

@router.get("/sub-districts", response_model=PaginatedListResponse[SubDistrictRead])
async def list_sub_districts(
    db: AsyncSessionDep,
    page: int = 1,
    items_per_page: int = 10,
    city_id: uuid_pkg.UUID | None = None,
) -> dict[str, Any]:
    skip = compute_offset(page, items_per_page)
    kwargs = {"deleted": False}
    if city_id:
        kwargs["city_id"] = city_id
    response = await crud_sub_districts.get_multi(
        db,
        offset=skip,
        limit=items_per_page,
        **kwargs
    )
    return paginated_response(crud_data=response, page=page, items_per_page=items_per_page)

@router.get("/sub-districts/{sub_district_id}", response_model=SubDistrictRead)
async def get_sub_district(
    sub_district_id: uuid_pkg.UUID,
    db: AsyncSessionDep,
) -> Any:
    return await crud_sub_districts.get(db, id=sub_district_id, deleted=False)
