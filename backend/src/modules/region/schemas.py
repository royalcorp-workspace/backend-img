from typing import Optional
from pydantic import BaseModel, ConfigDict
import uuid as uuid_pkg
from datetime import datetime

class ProvinceRead(BaseModel):
    id: uuid_pkg.UUID
    name: str
    code: Optional[str]
    is_active: bool
    sort_order: int
    model_config = ConfigDict(from_attributes=True)

class CityRead(BaseModel):
    id: uuid_pkg.UUID
    province: str
    province_id: Optional[str]
    name: str
    is_active: bool
    sort_order: int
    model_config = ConfigDict(from_attributes=True)

class SubDistrictRead(BaseModel):
    id: uuid_pkg.UUID
    province: str
    province_id: Optional[str]
    city_id: uuid_pkg.UUID
    district: str
    sub_district: str
    postal_code: str
    is_active: bool
    sort_order: int
    model_config = ConfigDict(from_attributes=True)
