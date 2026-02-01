from fastapi import APIRouter, Depends, HTTPException, Security, Query
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.db.session import get_db
from app.core.config import settings
from app.models.orm import Organization, Activity, Building
from app.schemas.all_schemas import OrganizationRead, BuildingRead
from app.services.business import (
    get_activity_subtree_ids, 
    get_organizations_in_radius, 
    get_organizations_in_bbox,
    get_buildings_in_radius,
    get_buildings_in_bbox
)

router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == settings.API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")


@router.get("/buildings/{building_id}/organizations", response_model=List[OrganizationRead])
async def get_organizations_by_building(
    building_id: int,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key)
):
    # список всех организаций в здании
    stmt = select(Organization).options(
        selectinload(Organization.building),
        selectinload(Organization.activities),
        selectinload(Organization.phones)
    ).where(Organization.building_id == building_id)
    
    result = await session.execute(stmt)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/buildings/search/geo", response_model=List[BuildingRead])
async def search_buildings_geo(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius: Optional[float] = Query(None),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    session: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key)
):
    # поиск зданий: радиус или квадрат
    if lat is not None and lon is not None and radius is not None:
        return await get_buildings_in_radius(session, lat, lon, radius)
    
    if all(v is not None for v in [min_lat, max_lat, min_lon, max_lon]):
        return await get_buildings_in_bbox(session, min_lat, max_lat, min_lon, max_lon)
        
    raise HTTPException(status_code=400, detail="Provide either (lat, lon, radius) or (min_lat, max_lat, min_lon, max_lon)")

@router.get("/buildings/", response_model=List[BuildingRead])
async def get_all_buildings(
    session: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key)
):
    stmt = select(Building)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/activities/{activity_id}/organizations", response_model=List[OrganizationRead])
async def get_organizations_by_activity(
    activity_id: int,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key)
):
    # рекурсивный поиск по дереву категорий
    # если ищем "Еда", должны найти и "Мясо", и "Молоко"
    activity_ids = await get_activity_subtree_ids(session, activity_id)
    
    if not activity_ids:
        raise HTTPException(status_code=404, detail="Activity not found")

    stmt = select(Organization).join(Organization.activities).options(
        selectinload(Organization.building),
        selectinload(Organization.activities),
        selectinload(Organization.phones)
    ).where(Activity.id.in_(activity_ids)).distinct()
    
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/organizations/search/geo", response_model=List[OrganizationRead])
async def search_organizations_geo(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius: Optional[float] = Query(None),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    session: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key)
):
    # два режима поиска: радиус или квадрат
    # если передали точку и радиус - считаем расстояние
    if lat is not None and lon is not None and radius is not None:
        return await get_organizations_in_radius(session, lat, lon, radius)
    
    # если передали границы - ищем в квадрате
    if all(v is not None for v in [min_lat, max_lat, min_lon, max_lon]):
        return await get_organizations_in_bbox(session, min_lat, max_lat, min_lon, max_lon)
        
    raise HTTPException(status_code=400, detail="Provide either (lat, lon, radius) or (min_lat, max_lat, min_lon, max_lon)")

@router.get("/organizations/search/name", response_model=List[OrganizationRead])
async def search_organizations_by_name(
    q: str = Query(...),
    session: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key)
):
    # простой поиск по названию (ilike)
    stmt = select(Organization).options(
        selectinload(Organization.building),
        selectinload(Organization.activities),
        selectinload(Organization.phones)
    ).where(Organization.name.ilike(f"%{q}%"))
    
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/organizations/{organization_id}", response_model=OrganizationRead)
async def get_organization_detail(
    organization_id: int,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key)
):
    stmt = select(Organization).options(
        selectinload(Organization.building),
        selectinload(Organization.activities),
        selectinload(Organization.phones)
    ).where(Organization.id == organization_id)
    
    result = await session.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org
