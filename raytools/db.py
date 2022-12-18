from sqlmodel import SQLModel, create_engine, Session

class Database:
    def __init__(self, path):
        connect_args = {"check_same_thread": False}
        Database.engine = create_engine(f"sqlite:///{path}", connect_args=connect_args)
        SQLModel.metadata.create_all(Database.engine)
    def session(self):
        return Session(self.engine)