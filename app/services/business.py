from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.orm import Activity, Organization, Building

async def get_activity_subtree_ids(session: AsyncSession, root_id: int) -> List[int]:
    # рекурсивно забираем все id вложенных категорий
    # используем CTE, чтобы не грузить питон лишними запросами
    base_query = select(Activity.id).where(Activity.id == root_id).cte("activity_cte", recursive=True)
    
    recursive_part = select(Activity.id).join(
        base_query, Activity.parent_id == base_query.c.id
    )
    
    cte = base_query.union_all(recursive_part)
    
    result = await session.execute(select(cte.c.id))
    return result.scalars().all()

async def check_activity_depth(session: AsyncSession, parent_id: Optional[int]) -> bool:
    # проверяем вложенность (макс 3 уровня)
    # если родителя нет, то это корневая категория (уровень 1) -> ок
    if parent_id is None:
        return True
    
    # считаем всех предков
    query = select(Activity).where(Activity.id == parent_id).cte("ancestors", recursive=True)
    parent_part = select(Activity).join(query, Activity.id == query.c.parent_id)
    cte = query.union_all(parent_part)
    
    result = await session.execute(select(func.count()).select_from(cte))
    count = result.scalar_one()

    
    return count < 3

async def get_organizations_in_radius(session: AsyncSession, lat: float, lon: float, radius_km: float) -> List[Organization]:
    # ищем соседей через haversine
    # формула гаверсинуса в sql, потому что postgis тянуть ради этого оверкилл
    earth_radius = 6371
    
    # хардкорная математика
    # d = 2 * R * asin... но через acos обычно стабильнее в базы ложится
    stmt = select(Organization).join(Building).options(
        selectinload(Organization.building),
        selectinload(Organization.activities),
        selectinload(Organization.phones)
    ).where(
        (
            earth_radius * func.acos(
                func.cos(func.radians(lat)) * 
                func.cos(func.radians(Building.latitude)) * 
                func.cos(func.radians(Building.longitude) - func.radians(lon)) + 
                func.sin(func.radians(lat)) * 
                func.sin(func.radians(Building.latitude))
            )
        ) <= radius_km
    )
    
    result = await session.execute(stmt)
    return result.scalars().all()

async def get_organizations_in_bbox(session: AsyncSession, min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> List[Organization]:
    # поиск квадратом (bbox)
    stmt = select(Organization).join(Building).options(
        selectinload(Organization.building),
        selectinload(Organization.activities),
        selectinload(Organization.phones)
    ).where(
        and_(
            Building.latitude >= min_lat,
            Building.latitude <= max_lat,
            Building.longitude >= min_lon,
            Building.longitude <= max_lon
        )
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_buildings_in_radius(session: AsyncSession, lat: float, lon: float, radius_km: float) -> List[Building]:
    earth_radius = 6371
    stmt = select(Building).where(
        (
            earth_radius * func.acos(
                func.cos(func.radians(lat)) * 
                func.cos(func.radians(Building.latitude)) * 
                func.cos(func.radians(Building.longitude) - func.radians(lon)) + 
                func.sin(func.radians(lat)) * 
                func.sin(func.radians(Building.latitude))
            )
        ) <= radius_km
    )
    result = await session.execute(stmt)
    return result.scalars().all()

async def get_buildings_in_bbox(session: AsyncSession, min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> List[Building]:
    stmt = select(Building).where(
        and_(
            Building.latitude >= min_lat,
            Building.latitude <= max_lat,
            Building.longitude >= min_lon,
            Building.longitude <= max_lon
        )
    )
    result = await session.execute(stmt)
    return result.scalars().all()
