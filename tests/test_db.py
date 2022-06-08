import pytest
from ccrawl.conf import Config
from ccrawl.db import *


def test_Proxy_tinydb(configfile, db_doc1, db_doc2):
    c = Config(configfile)
    c.Database.local = u""
    c.Database.url = u""
    db = Proxy(c.Database)
    assert db.c == c.Database
    assert type(db.ldb).__name__ == "TinyDB"
    assert db.ldb.storage.__class__.__name__ == "MemoryStorage"
    assert db.rdb is None
    assert len(list(db.ldb)) == 0
    db.ldb.insert(db_doc1)
    assert db.ldb.contains(where("id") == "xxx")
    db.insert_multiple(db_doc2)
    x = db.get(where("id") == "struct X")
    assert x["cls"] == "cStruct"
    assert len(db.search(where("cls") == "cTypedef")) == 2
    db.close()


def test_Proxy_mongodb(configfile, db_doc2):
    c = Config(configfile)
    c.Database.local = u""
    db = Proxy(c.Database)
    # TODO
