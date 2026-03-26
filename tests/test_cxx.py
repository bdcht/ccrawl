import pytest
from click.testing import CliRunner
from ccrawl.main import *

def test_create_db(configfile, dbfilexx, cxx_headers):
    runner = CliRunner()
    result = runner.invoke(
            cli,
            [
              "-l",
              dbfilexx,
              "-c",
              configfile,
              "collect",
            ]+cxx_headers,
    )
    assert result.exit_code == 0

def test_MyClass(configfile,dbfilexx):
    c = conf.Config(configfile)
    c.Database.url = u""
    c.Database.local = dbfilexx
    db = Proxy(c.Database)
    assert type(db.ldb).__name__ == "TinyDB"
    x = db.get(where("id")=="class MyClass")
    assert x["cls"]=="cClass"
    x = ccore.from_db(x)
    assert x.identifier == "class MyClass"
    s = x.as_cStruct(db)
    assert len(s)==4
    assert s[0]==('void *', '__vptr$MyClass', '')
    assert s[1]==('int', 'field', '')
    assert s[2]==('int *', 'pubfield', '')
    assert s[3]==('const int', 'static_field', '')

def test_classM(configfile,dbfilexx):
    c = conf.Config(configfile)
    c.Database.url = u""
    c.Database.local = dbfilexx
    db = Proxy(c.Database)
    x = ccore.from_db(db.get(where("id")=="class M"))
    x.unfold(db)
    assert 'T' in x.subtypes
    t = x.subtypes['T']
    assert 'S' in t.subtypes
    s = t.subtypes['S']
    assert 'std::basic_string<char>' in s.subtypes
    assert 'oldstruct' in s.subtypes

def test_L2(configfile,dbfilexx):
    c = conf.Config(configfile)
    c.Database.url = u""
    c.Database.local = dbfilexx
    db = Proxy(c.Database)
    x = ccore.from_db(db.get(where("id")=="L2"))
    t = str(x)
    assert t=='L1::Level2<bars::Bar>'
    x.unfold(db)
    assert 'L1' in x.subtypes
    assert 'bars' in x.subtypes
    assert 'bars::Bar' in x.subtypes
    assert t in x.subtypes
    xt = x.subtypes[t]
    assert xt.identifier == 'struct Level2<T1>'
    assert xt.ns == 'Level1<T0>'
    l1 = x.subtypes['L1']
    assert 'struct Level1<bars::Bar<void>>' in l1.subtypes
    assert 'bars::Bar<void>' in l1.subtypes





