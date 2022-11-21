from re import compile as recompile, sub as resub
from json import load as jsonload, dump as jsondump

"""
Quickly query/modify the database without any SQL knowledge
"""

class Database(object):
    con = None
    cur = None
    def __init__(self, db_path="customers.db"):
        import sqlite3
        sqlite3_create_tables = """CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY,
username TEXT UNIQUE NOT NULL,
count INTEGER NOT NULL,
uuid TEXT UNIQUE NOT NULL,
disabled INTEGER
);
CREATE TABLE IF NOT EXISTS sales (
id INTEGER PRIMARY KEY,
user_id INTEGER NOT NULL,
date INTEGER NOT NULL,
days INTEGER,
paid INTEGER,
start INTEGER,
FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS telegram (
id INTEGER PRIMARY KEY,
user_id INTEGER NOT NULL,
tg_id INTEGER UNIQUE,
FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS servers (
id INTEGER PRIMARY KEY,
name TEXT NOT NULL UNIQUE,
address TEXT NOT NULL,
link TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rservers (
id INTEGER PRIMARY KEY,
address TEXT NOT NULL UNIQUE
);
"""
        Database.con = sqlite3.connect(db_path)
        Database.cur = Database.con.cursor()
        Database.cur.executescript(sqlite3_create_tables)

def add_user(
        db, # Database object
        username,
        count, # Number of devices allowed
        uuid,
        nocommit=None,
        ):
    pattern_uuid = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
    if not recompile(pattern_uuid).match(uuid): # Just an extra check. Doesn't have to be here
        raise ValueError("Invalid UUID")
    db.cur.execute("INSERT INTO users (username, count, uuid) VALUES (?, ?, ?)", (username, count, uuid))
    if not nocommit:
        db.con.commit()

def add_payment(
        db,
        query=None,
        date=None, # Payment date
        days=None, # Length of subscription
        paid=None, # How much the user has paid
        start=False, # Is this the start of user's subscription
        nocommit=None,
        ):
    res = select(db, "users", columns=("id"), query=query).fetchmany(size=2)
    res = _return_one(res)
    db.cur.execute(
            "INSERT INTO sales (user_id, date, days, paid, start) VALUES (?, ?, ?, ?, ?)",
            (res[0], date, days, paid, start),
            )
    if not nocommit:
        db.con.commit()

def add_tg( # Links users in telegram table to a user in users table
        db,
        tg_id,
        query=None,
        nocommit=None,
        ):
    res = select(db, "users", columns=("id"), query=query).fetchmany(size=2)
    res = _return_one(res)
    db.cur.execute(
            "INSERT INTO telegram (user_id, tg_id) VALUES (?, ?)",
            (tg_id, res[0]),
            )
    if not nocommit:
        db.con.commit()

def add_server(
        db,
        name,
        address,
        link,
        nocommit=None,
        ):
    if not isinstance(link, str):
        raise TypeError("Invalid Type")
    #matched = recompile(r'^(vmess|vless)://(.+)').match(link)
    #if not matched or len(matched) != 3:
    #    raise ValueError("Invalid Link")
    db.cur.execute(
            "INSERT INTO servers (name, address, link) VALUES (?, ?, ?)",
            (name, address, link)
            )
    if not nocommit:
        db.con.commit()

def add_rserver(
        db,
        address,
        nocommit=None,
        ):
    db.cur.execute("INSERT INTO rservers (address) VALUES (?)", address)
    if not nocommit:
        db.con.commit()

def get_tg(
        db,
        **kwargs,
        ):
    res = select(db, "telegram", **kwargs).fetchmany(size=2)
    return _return_one(res)

def get_users( # Returns: [(1,1,1),(2,2,2)]
        db, # Database object
        size=1,
        **kwargs,
        ):
    res = select(db, "users", **kwargs)
    if size == 0:
        res = res.fetchall()
    res = res.fetchmany(size=size)
    if not res:
        raise IndexError("Emtpy result")
    return res

def getall_users(*args, **kwargs):
    return get_users(*args, **{**kwargs, "size": 0})

def get_user(*args, **kwargs):
    return get_users(*args, **{**kwargs, "size": 1})[0]

def get_server(
        db,
        **kwargs,
        ):
    res = select(db, "servers", **kwargs).fetchone()
    if not res:
        raise IndexError("Emtpy result")
    return res

def disable_user(
        db,
        query=None,
        disabled=True,
        nolimit=None,
        nocommit=None,
        ):
    query = makequery(query)
    limit = "" if nolimit else " LIMIT 1"
    db.cur.execute("UPDATE users SET disabled = ?" + query + limit, (disabled, *query[1]))
    if not nocommit:
        db.con.commit()

def enable_user(*args, **kwargs):
    disable_user(*args, **{**kwargs, "disabled": False})

def delete_user( # !!! DANGEROUS !!!
        db, # Database object
        nocommit=None,
        **kwargs,
        ):
    # Disable the user instead
    # Backup your database before running this function. Do it multiple times just in case
    raise Exception("Don't do this please.") # comment this line (DANGEROUS)
    # !!! DANGEROUS !!!
    res = select(db, "users", **kwargs).fetchmany(size=2)
    res = _return_one(res)[0]
    db.cur.execute("DELETE FROM sales WHERE user_id = ?", (res,))
    db.cur.execute("DELETE FROM telegram WHERE user_id = ?", (res,))
    db.cur.execute("DELETE FROM users WHERE id = ? LIMIT 1", (res,))
    if not nocommit:
        db.con.commit()

def mod_user(
        db,
        query=None, # An array or a tuple: (column name, query)
        modify={}
        nocommit=None,
        nolimit=None,
        **kwargs, # columns to be changed
        ):
    query = makequery(query)
    if not modify:
        raise IndexError("Nothing to do")
    set_string = []
    for key in modify:
        if not _matchword(key):
            raise Exception("Invalid keyword")
        set_string.append("{} = ?".format(key))
    limit = "" if nolimit else " LIMIT 1"
    res = db.cur.execute(
            "UPDATE users SET {}".format(', '.join(set_string)) + query[0] + limit,
            (*modify.values() ,*query[1]),
            )
    if not nocommit:
        db.con.commit()

def _return_one(res, soft=None):
    if len(res) == 1:
        return res[0]
    if soft:
        return
    if not res:
        raise IndexError("Could not find the given query")
    else:
        raise IndexError("Found too many rows with the given query")

def _matchword(text):
    if not text:
        return None
    return recompile(r'^[0-9A-Za-z\_]{,24}$').match(text)

def select(db, table, query=None, columns=None):
    if not _matchword(table):
        raise Exception("Knock Knock")
    print(query)
    query = makequery(query)
    columns = makecolumns(columns)
    return db.cur.execute(f"SELECT {columns} FROM {table}" + query[0], *query[1])

def makecolumns(columns):
    if not columns or columns == "*":
        return "*"
    if not isinstance(columns, tuple):
        raise TypeError("Invalid Type")
    if not all([isinstance(i, str) for i in query]):
        raise TypeError("Invalid Type")
    if not all([_matchword(i) for i in columns]):
        raise Exception("SQL Inje... We don't do that here")
    return ', '.join(columns)

def makequery(query):
    if not query:
        return ("", ())
    operations = ["=", "!=", "LIKE", "IS", "IS NOT"]
    if not isinstance(query, tuple):
        raise TypeError("Invalid Type")
    if len(query) != 3:
        raise IndexError("Query needs to be a tuple containing the column name, operation and the query")
    if not all([isinstance(i, str) for i in query]):
        raise TypeError("Invalid Type")
    if not _matchword(query[0]):
        raise Exception("SQL Injecting? WHY?")
    if not query[1] in operations:
        raise ValueError("Invalid Operation")
    return (" WHERE {} {} ?".format(*query[:2]), (query[2],))
