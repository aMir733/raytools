"""
Database models are defined here
"""
from typing import List, Optional
from sqlmodel import SQLModel, Relationship, Columns, String, ARRAY
#from sqlalchemy.dialects.postgresql import ARRAY

"""Base structure for tables"""
class Base(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)

class User(Base, table = True):
    username: str = Field(sa_column_kwargs={"unique": True})
    count: int
    uuid: str = Field(sa_column_kwargs={"unique": True})
    disabled: Optional[bool] = Field(default=False)
    plan_id: int = Field(foreign_key="plan.id")
    plan: Plan = Relationship(back_populates="users")
    sales: List["Sale"] = Relationship(back_populates="user")
    telegrams: List["Telegram"] = Relationship(back_populates="user")

class Plan(Base, table = True):
    servers: Set[str] = Field(sa_column=Column(ARRAY(String())))
    users: List["User"] = Relationship(back_populates="plan")

class Sale(Base, table = True):
    date: int
    days: Optional[int]
    paid: Optional[int]
    start: Optional[bool]
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="sales")

class Telegram(Base, table = True):
    tg_id: int
    user_id: int = Field(foreign_key="user.id", sa_column_kwargs={"unique": True})
    user: User = Relationship(back_populates="telegrams")

class Server(Base, table = True):
    name: str = Field(sa_column_kwargs={"unique": True})
    address: str
    link: str

class Rserver(Base, table = True):
    address: str = Field(sa_column_kwargs={"unique": True})
