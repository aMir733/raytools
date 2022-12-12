from sqlmodel import SQLModel, create_engine, Session

class Database:
    def __init__(self, path):
        Database.engine = create_engine(f"sqlite:///{path}")
        SQLModel.metadata.create_all(Database.engine)
    def session(self):
        return Session(self.engine)