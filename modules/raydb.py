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
protocol TEXT NOT NULL CHECK (protocol = 'vmess' OR protocol = 'vless'),
link TEXT
);
CREATE TABLE IF NOT EXISTS rservers (
id INTEGER PRIMARY KEY,
address TEXT NOT NULL UNIQUE
);
"""
        self.con = sqlite3.connect(db_path)
        self.cur = Database.con.cursor()
        self.cur.executescript(sqlite3_create_tables)

def make_config(
        clients, # List of clients to add to configuration: [(x,y,z),(a,b,c)]
        path, # Path to your configuration file
        dest="config_new.json", # Where to store the new configuration file
        ):
    if type(clients) != list:
        raise TypeError("Invalid type for clients. Only lists are acceptable")
    with open(path, "r") as f:
        js = jsonload(f)
    if not 'inbounds' in js:
        raise KeyError("Could not find the 'inbounds' entry in {} . If you're using the 'inbound' keyword please change it to 'inbounds'".format(path))
    passed = None
    for inbound in js['inbounds']:
        if inbound['protocol'] != 'vmess' and inbound['protocol'] != 'vless':
            continue
        default_client = inbound['settings']['clients'][0]
        if default_client['email'] != "v2ray_tools":
            continue
        passed = True
        max_digits = len(str(max(clients)[0]))
        for client in clients:
            inbound['settings']['clients'].append({
                **default_client,
                "id": client[3], # uuid
                "email": str(client[0]).zfill(max_digits), # email
            })
    if passed != True:
        raise ValueError("Could not find an appropriate inbound")
    with open(dest, "w") as f:
        jsondump(js, f)
    return dest

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
        query, # An array or a tuple: (column name, query)
        date=None, # Payment date
        days=None, # Length of subscription
        paid=None, # How much the user has paid
        start=False, # Is this the start of user's subscription
        nocommit=None,
        ):
    _check_query(query)
    res = db.cur.execute(
            "SELECT id FROM users WHERE {} LIKE ?".format(query[0]),
            (query[1],),
            ).fetchmany(size=2)
    res = _return_one(res)
    db.cur.execute(
            "INSERT INTO dates (user_id, date, days, paid, start) VALUES (?, ?, ?, ?, ?)",
            (res[0], date, days, paid, start),
            )
    if not nocommit:
        db.con.commit()

def add_tg( # Links users in telegram table to a user in users table
        db,
        query,
        tg_id,
        nocommit=None,
        ):
    _check_query(query)
    res = db.cur.execute(
            "SELECT id FROM users WHERE {} LIKE ?".format(query[0]),
            (query[1],),
            ).fetchmany(size=2)
    res = _return_one(res)
    db.cur.execute(
            "INSERT INTO telegram (user_id, tg_id) VALUES (?, ?)",
            (tg_id, res[0]),
            )
    if not nocommit:
        db.con.commit()

def add_srv(
        db,
        name,
        address,
        protocol=None,
        link=None,
        nocommit=None,
        ):
    if isinstance(link, dict):
        link = jsondumps(link)
    if link != None and not isinstance(link, str):
        raise TypeError("Invalid Type")
    if link:
        matched = recompile(r'^(vmess|vless)://(.*)').match(link)
        if len(matched) == 3:
            protocol = matched[1]
            link = matched[2]
    if not protocol:
        raise TypeError("Protocol was not specified")
    db.cur.execute(
            "INSERT INTO servers (name, address, type, link) VALUES (?, ?, ?, ?)",
            (name, address, protocol, link)
            )
    if not nocommit:
        db.con.commit()

def get_tg( # Returns the user id associated with query
        db,
        query,
        full=None, # If true it will return every column instead of just id
        ):
    _check_query(query)
    if full:
        cmd = "SELECT * FROM users WHERE telegram.{} = ?"
    else:
        cmd = "SELECT user_id FROM telegram WHERE {} = ?"
    res = db.cur.execute(
            cmd.format(query[0]),
            (query[1],)
            ).fetchmany(size=2)
    res = _return_one(res)
    return res if full else res[0]

def getall_users(
        db, # Database object
        ):
    return db.cur.execute("SELECT * FROM users").fetchall()

def get_users( # Returns: [(1,1,1),(2,2,2)]
        db, # Database object
        query, # An array or a tuple: (column name, query)
        size=1,
        ):
    _check_query(query)
    res = db.cur.execute("SELECT * FROM users WHERE {} LIKE ?".format(query[0]), (query[1],))
    if size == 0:
        return res.fetchall()
    #if size == 1: <--- commented: Inconsistent return value
    #    return res.fetchone()
    return res.fetchmany(size=size)

def get_user(*args, **kwargs): # Returns (1,1,1)
    res = get_users(*args, **{**kwargs, "size": 1})
    return res[0] if res else res

def disable_user(
        db,
        query,
        disabled=True,
        nolimit=None,
        nocommit=None,
        ):
    _check_query(query)
    limit = "" if nolimit else " LIMIT 1"
    db.cur.execute("UPDATE users SET disabled = ? WHERE {} LIKE ?".format(query[0],) + limit, (disabled, query[1]))
    if not nocommit:
        db.con.commit()

def enable_user(*args, **kwargs):
    disable_user(*args, **{**kwargs, "disabled": False})

def delete_user( # !!! DANGEROUS !!!
        db, # Database object
        query, # An array or a tuple: (column name, query)
        nocommit=None
        ):
    # Run the dis_user function insted
    # Backup your database before running this function. Do it multiple times just in case
    raise Exception("Don't do this please. Run the dis_user instead") # comment this line (DANGEROUS)
    # !!! DANGEROUS !!!
    _check_query(query)
    res = db.cur.execute(
            "SELECT id FROM users WHERE {} LIKE ?".format(query[0]),
            (query[1],)
            ).fetchmany(size=2)
    res = _return_one(res)[0]
    db.cur.execute("DELETE FROM sales WHERE user_id = ?", (res,))
    db.cur.execute("DELETE FROM telegram WHERE user_id = ?", (res,))
    db.cur.execute("DELETE FROM users WHERE id = ? LIMIT 1", (res,))
    if not nocommit:
        db.con.commit()

def mod_user(
        db,
        query, # An array or a tuple: (column name, query)
        nocommit=None,
        nolimit=None,
        **kwargs, # columns to be changed
        ):
    _check_query(query)
    if len(kwargs) < 1:
        raise IndexError("At least one kwarg is required for this function")
    set_string = []
    pattern_word = r'^[0-9A-Za-z]{,24}$'
    for kwarg in kwargs:
        _check_query((kwarg, None))
        set_string.append("{} = ?".format(kwarg))
    limit = "" if nolimit else " LIMIT 1"
    res = db.cur.execute(
            "UPDATE users SET {} WHERE {} = ?".format(', '.join(set_string) + limit, query[0]),
            tuple(kwargs.values()) + (query[1],)
            )
    if not nocommit:
        db.con.commit()

def _return_one(res, soft=None):
    if len(res) == 1:
        return res[0]
    if soft:
        return
    if len(res) == 0:
        raise ValueError("Could not find the given query")
    else:
        raise ValueError("Found too many users with the given query")

def _check_query(query):
    pattern_word = r'^[0-9A-Za-z\_]{,24}$'
    if len(query) != 2:
        raise ValueError("Query needs to be a tuple containing the column name and the query")
    if not recompile(pattern_word).match(query[0]):
        raise ValueError("No SQL Injection allowed")
