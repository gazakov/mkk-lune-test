import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import Activity, Building, Organization

pytestmark = pytest.mark.asyncio

async def test_empty_db(client: AsyncClient):
    """
    Verify 200 OK and empty list on empty database.
    """
    response = await client.get("/organizations/search/name?q=NonExistent")
    assert response.status_code == 200
    assert response.json() == []

async def test_auth_failure(client: AsyncClient):
    """
    Verify 403 Forbidden when API Key is missing/invalid.
    """
    client.headers.pop("X-API-Key", None)
    response = await client.get("/organizations/search/name?q=test")
    assert response.status_code == 403

async def test_create_deep_nesting_and_search(session: AsyncSession, client: AsyncClient):
    """
    Scenario: Deep Nesting + Recursion Search.
    Tree: Root -> Child -> Grandchild
    Search for 'Root' should return Org assigned to 'Grandchild'.
    """
    root = Activity(name="Root")
    session.add(root)
    await session.flush()
    
    child = Activity(name="Child", parent_id=root.id)
    session.add(child)
    await session.flush()
    
    grandchild = Activity(name="Grandchild", parent_id=child.id)
    session.add(grandchild)
    await session.flush()
    
    # Building
    b = Building(address="Test St", latitude=0, longitude=0)
    session.add(b)
    await session.flush()
    
    org = Organization(name="Deep Org", building_id=b.id, activities=[grandchild])
    session.add(org)
    await session.commit()

    # Test Search by Root
    response = await client.get(f"/activities/{root.id}/organizations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deep Org"
    assert data[0]["activities"][0]["name"] == "Grandchild"

async def test_max_depth_constraint(session: AsyncSession, client: AsyncClient):
    """
    Scenario: Constraint.
    Try to create a 4th level.
    Root (1) -> Child (2) -> Grandchild (3) -> Grants-Grandchild (4)
    Ideally tested via Unit Test on Service, but here we can setup DB and try logic check if exposed.
    Since endpoints usually read, we might rely on the 'check_activity_depth' function strictly if we had a write endpoint.
    However, the prompt asks to 'Constraint: Try to create...'. 
    If there is no 'create activity' endpoint, we should test the service function directly or assume we verify the logic via unit test style here.
    Let's test the service function directly for this specific constraint logic.
    """
    from app.services.business import check_activity_depth
    
    l1 = Activity(name="L1")
    session.add(l1)
    await session.flush()
    
    l2 = Activity(name="L2", parent_id=l1.id)
    session.add(l2)
    await session.flush()
    
    l3 = Activity(name="L3", parent_id=l2.id)
    session.add(l3)
    await session.flush()
    
  
    is_allowed = await check_activity_depth(session, l3.id)
    assert is_allowed is False, "Should not allow nesting deeper than 3 levels"

    is_allowed_ok = await check_activity_depth(session, l2.id)
    assert is_allowed_ok is True

async def test_geo_exact_hit(session: AsyncSession, client: AsyncClient):
    """
    Scenario: Exact Hit.
    Org at 100m distance. Search radius 200m.
    """
    lat, lon = 55.7558, 37.6173
    
    b = Building(address="Near", latitude=lat + 0.0005, longitude=lon) 
    session.add(b)
    await session.flush()
    
    org = Organization(name="Near Org", building_id=b.id)
    session.add(org)
    await session.commit()
    
    response = await client.get(f"/organizations/search/geo?lat={lat}&lon={lon}&radius=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Near Org"

async def test_geo_miss(session: AsyncSession, client: AsyncClient):
    """
    Scenario: Miss.
    Org at 5km distance. Search radius 1km.
    """
    lat, lon = 55.7558, 37.6173
    
    b = Building(address="Far", latitude=lat + 0.05, longitude=lon)
    session.add(b)
    await session.flush()
    
    org = Organization(name="Far Org", building_id=b.id)
    session.add(org)
    await session.commit()
    
    response = await client.get(f"/organizations/search/geo?lat={lat}&lon={lon}&radius=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

async def test_geo_coordinates_validation(client: AsyncClient):
    """
    Scenario: Coordinates Warning/Validation.
    Lat 91 should fail if validated, or logical handling.
    The schema has validation.
    """
    response = await client.get("/organizations/search/geo?lat=91&lon=0&radius=1")
    assert response.status_code == 422

async def test_not_found(client: AsyncClient):
    """
    Scenario: 404 on Not Found.
    """
    response = await client.get("/organizations/999999")
    assert response.status_code == 404
