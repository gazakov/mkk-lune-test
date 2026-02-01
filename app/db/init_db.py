from sqlalchemy import select
from app.models.orm import Activity, Building, Organization, OrganizationPhone
from sqlalchemy.orm import selectinload
from app.db.session import engine, Base, AsyncSessionLocal

async def init_db():
    # в проде конечно лучше alembic, но для теста сойдет и create_all
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Activity))
        if result.first():
            return

        # наливаем тестовые данные
        # 1. категории
        food = Activity(name="Еда")
        cars = Activity(name="Автомобили")
        session.add_all([food, cars])
        await session.flush()

        # уровень 2
        meat = Activity(name="Мясная продукция", parent_id=food.id)
        milk = Activity(name="Молочная продукция", parent_id=food.id)
        spare_parts = Activity(name="Запчасти", parent_id=cars.id)
        session.add_all([meat, milk, spare_parts])
        await session.flush()
        
        # уровень 3
        beef = Activity(name="Говядина", parent_id=meat.id) 
        tires = Activity(name="Шины", parent_id=spare_parts.id)
        session.add_all([beef, tires])
        await session.flush()

        # 2. здания (центр москвы и рядом)
        b1 = Building(address="г. Москва, ул. Ленина 1", latitude=55.7558, longitude=37.6173) 
        b2 = Building(address="г. Москва, ул. Пушкина 2", latitude=55.751244, longitude=37.618423)
        session.add_all([b1, b2])
        await session.flush()

        # 3. организации
        org1 = Organization(name="ООО Рога и Копыта", building_id=b1.id)
        org2 = Organization(name="Молочный Мир", building_id=b2.id)
        org_auto = Organization(name="Шиномонтаж у Ашота", building_id=b1.id)
        
        session.add_all([org1, org2, org_auto])
        await session.flush()
        
        # проставляем связи
        # логика такая: если контора торгует говядиной, прикручиваем ей и "мясо", и "говядину"
        # хотя по-хорошему рекурсивный поиск сам должен находить
        
        # FIX: Pre-load activities to avoid MissingGreenlet (Async Lazy Load)
        await session.execute(
            select(Organization)
            .options(selectinload(Organization.activities))
            .where(Organization.id.in_([org1.id, org2.id, org_auto.id]))
        )
        
        org1.activities.append(meat)
        org1.activities.append(beef)
        
        org2.activities.append(milk)
        org_auto.activities.append(tires)
        
        # 4. телефоны
        p1 = OrganizationPhone(number="8-800-555-35-35", organization_id=org1.id)
        p2 = OrganizationPhone(number="2-22-33", organization_id=org1.id)
        session.add(p1)
        session.add(p2)
        
        await session.commit()
