import pytest
import os
from click.testing import CliRunner
from ccrawl.main import *

def test_ctypes_01(dbfile):
    runner = CliRunner()
    inc = os.path.dirname(__file__)
    result = runner.invoke(cli, ['-l',dbfile,'-b','None',
                          'collect','--clang','"-I%s/samples"'%inc,
                          os.path.join(inc,
                                       'samples/header.h',
                                       )])
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


def test_ctypes_02(dbfile):
    runner = CliRunner()
    inc = os.path.dirname(__file__)
    result = runner.invoke(cli, ['-l',dbfile,'-b','None',
                          'collect', '-a',
                          os.path.join(inc, 'samples/shahar.cpp')])
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

def test_amoco_01(dbfile):
    runner = CliRunner()
    inc = os.path.dirname(__file__)
    result = runner.invoke(cli, ['-l',dbfile,'-b','None',
                          'collect',
                          os.path.join(inc, 'samples/header.h')])
    assert result.exit_code == 0
    conf.config = conf.Config()
    conf.config.Database.url = u''
    conf.config.Database.local = dbfile
    db = Proxy(conf.config.Database)
    x = ccore.from_db(db.get(where('id')=='struct _mystruct'))
    assert x._is_struct
    from ccrawl.ext import amoco
    from amoco.system.structs.core import StructCore
    cx = amoco.build(x,db)
    assert cx.__name__ == 'struct__mystruct'
    assert StructCore in cx.mro()
    assert cx.offset_of(cx,'p') == 52
    ax = cx()
    assert isinstance(ax,StructCore)
    assert ax.offset_of('p')==52
    assert cx.size(psize=8)==ax.size(psize=8)==104
    assert ax.fields[2].name == 'p'
    assert ax.fields[2].size(psize=8) == 16

