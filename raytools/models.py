"""
Database models are defined here
"""
from typing import Optional, List, Set
from sqlmodel import SQLModel, Field, Relationship, String, Column, JSON

"""Base structure for tables"""
class Base(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)

class Plan(Base, table = True):
    servers: Set[str] = Field(sa_column=Column(JSON))
    users: List["User"] = Relationship(back_populates="plan")
    class Config:
        arbitrary_types_allowed = True

class User(Base, table = True):
    username: str = Field(sa_column_kwargs={"unique": True}, index=True)
    count: int
    uuid: str = Field(sa_column_kwargs={"unique": True})
    disabled: Optional[str] = Field(default=None)
    sales: List["Sale"] = Relationship(back_populates="user")
    telegrams: List["Telegram"] = Relationship(back_populates="user")
    plan_id: Optional[int] = Field(default=0, foreign_key="plan.id")
    plan: Plan = Relationship(back_populates="users")

class Sale(Base, table = True):
    sdate: Optional[int] = Field(default=None)
    edate: int
    first: Optional[bool]
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="sales")

class Telegram(Base, table = True):
    tg_id: int = Field(index=True)
    user_id: int = Field(foreign_key="user.id", sa_column_kwargs={"unique": True})
    user: User = Relationship(back_populates="telegrams")

class Server(Base, table = True):
    name: str = Field(sa_column_kwargs={"unique": True})
    address: str
    link: str

class Rserver(Base, table = True):
    address: str = Field(sa_column_kwargs={"unique": True})
