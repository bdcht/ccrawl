import pytest
from click.testing import CliRunner
from ccrawl.main import *

def test_ctypes_01(dbfile):
    runner = CliRunner()
    result = runner.invoke(cli, ['-l',dbfile,'-b','None',
                          'collect', os.path.join(os.path.dirname(__file__), 'samples/header.h')])
    assert result.exit_code == 0
    conf.config = conf.Config()
    conf.config.Database.url = u''
    conf.config.Database.local = dbfile
    db = Proxy(conf.config.Database)
    x = ccore.from_db(db.get(where('id')=='struct _mystruct'))
    assert x._is_struct
    cx = x.build(db)
    assert type(cx).__name__ == 'PyCStructType'
    assert cx.p.offset == 52
    assert cx.p.size == 16


def test_ctypes_01(dbfile):
    runner = CliRunner()
    result = runner.invoke(cli, ['-l',dbfile,'-b','None',
                          'collect', '-a',
                          os.path.join(os.path.dirname(__file__), 'samples/shahar.cpp')])
    assert result.exit_code == 0
    conf.config = conf.Config()
    conf.config.Database.url = u''
    conf.config.Database.local = dbfile
    db = Proxy(conf.config.Database)
    x = ccore.from_db(db.get(where('id')=='struct K'))
    assert x._is_class
    cx = x.build(db)
    assert type(cx).__name__ == 'PyCStructType'
    f = cx._fields_
    assert f[0][0] == '__vptr$G'
    assert f[1][0] == 'b'
    assert f[2][0] == 'g'
    assert f[3][0] == 'i'
    assert f[4][0] == '__vptr$J'
    assert f[5][0] == 'j'
    assert f[6][0] == 'k'
    assert f[7][0] == 'a'
    assert f[8][0] == '__vptr$H'
    assert f[9][0] == 'b'
    assert f[10][0] == 'h'
