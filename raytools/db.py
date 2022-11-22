from sqlmodel import SQLModel, create_engine

class Database(object):
    def __init__(self, path):
        Database.engine = create_engine(f"sqlite:///{path}")
    def create(self):
        SQLModel.metadata.create_all(self.engine)
