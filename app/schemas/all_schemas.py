from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator

class BuildingBase(BaseModel):
    address: str
    latitude: float
    longitude: float

    @field_validator('latitude')
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not (-90 <= v <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @field_validator('longitude')
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if not (-180 <= v <= 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v

class BuildingCreate(BuildingBase):
    pass

class BuildingRead(BuildingBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ActivityBase(BaseModel):
    name: str

class ActivityCreate(ActivityBase):
    parent_id: Optional[int] = None

class ActivityRead(ActivityBase):
    id: int
    parent_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class ActivityTree(ActivityRead):
    children: List["ActivityTree"] = []

class PhoneBase(BaseModel):
    number: str

class PhoneCreate(PhoneBase):
    pass

class PhoneRead(PhoneBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class OrganizationBase(BaseModel):
    name: str
    building_id: int

class OrganizationCreate(OrganizationBase):
    activity_ids: List[int]
    phones: List[str]

class OrganizationRead(OrganizationBase):
    id: int
    building: BuildingRead
    activities: List[ActivityRead]
    phones: List[PhoneRead]
    model_config = ConfigDict(from_attributes=True)
