from typing import List, Optional
from sqlalchemy import String, Integer, Float, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

# таблица связей м2м
organization_activity = Table(
    "organization_activity",
    Base.metadata,
    Column("organization_id", Integer, ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
    Column("activity_id", Integer, ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
)

class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    address: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    organizations: Mapped[List["Organization"]] = relationship(back_populates="building")

class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    # дерево категорий (recursive adjacency list)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), nullable=True)

    children: Mapped[List["Activity"]] = relationship("Activity", back_populates="parent")
    parent: Mapped[Optional["Activity"]] = relationship("Activity", back_populates="children", remote_side=[id])
    organizations: Mapped[List["Organization"]] = relationship(secondary=organization_activity, back_populates="activities")

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))

    building: Mapped["Building"] = relationship(back_populates="organizations")
    activities: Mapped[List["Activity"]] = relationship(secondary=organization_activity, back_populates="organizations")
    phones: Mapped[List["OrganizationPhone"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

class OrganizationPhone(Base):
    __tablename__ = "organization_phones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    number: Mapped[str] = mapped_column(String)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))

    organization: Mapped["Organization"] = relationship(back_populates="phones")
