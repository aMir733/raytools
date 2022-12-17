"""
Database models are defined here
"""
from typing import Optional, List, Set
from sqlmodel import SQLModel, Field, Relationship, String, Column, JSON

"""Base structure for tables"""
class Base(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)

class User(Base, table = True):
    username: str = Field(sa_column_kwargs={"unique": True}, index=True)
    count: int
    uuid: str = Field(sa_column_kwargs={"unique": True})
    expires: int
    traffic: Optional[int] = Field(default=0)
    disabled: Optional[str] = Field(default=None)
    telegrams: List["Telegram"] = Relationship(back_populates="user")

class Telegram(SQLModel, table = True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="telegrams")

class Server(Base, table = True):
    name: str = Field(sa_column_kwargs={"unique": True})
    address: str
    link: str

class Rserver(Base, table = True):
    address: str = Field(sa_column_kwargs={"unique": True})
