import sys
from sqlmodel import select
from raytools.db import Database
from raytools.models import *
from raytools.func import parse_date

db = Database(sys.argv[1])
database = db.session()

now = parse_date("now")
users = database.exec(select(User).where(User.disabled == "expired", User.expires > now)).all()
for user in users:
    print(user)
    user.disabled = None
    database.add(user)
database.commit()
