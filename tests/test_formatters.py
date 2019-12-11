import pytest
from ccrawl.parser import ccore,parse
from ccrawl.formatters import *

def test_format_C(configfile,c_header):
    c = conf.Config(configfile)
    conf.config = c
    defs = list(parse(c_header,tag='test'))
    x = ccore.from_db(defs[0])
    assert x._is_macro
    assert x.show(form='C') == '#define MYCONST  0x10;'
    x = ccore.from_db(defs[5])
    assert x._is_typedef
    assert x.show(form='C') == 'typedef int (*foo)(int, char, unsigned int, void *);'
    x = ccore.from_db(defs[8])
    assert x._is_typedef
    assert x.show(form='C') == 'typedef void *(*(*foo2[2])(int, void **))[3];'
    x = ccore.from_db(defs[10])
    assert x._is_struct
    assert x.show(form='C') == """struct _mystruct {
  myinteger I;
  int tab[12];
  unsigned char p[16];
  short *s;
  struct _mystruct *next;
  foo func;
  struct _bar bar[2];
};"""

def test_format_ctypes(configfile,c_header):
    c = conf.Config(configfile)
    conf.config = c
    defs = list(parse(c_header,tag='test'))
    x = ccore.from_db(defs[0])
    assert x._is_macro
    assert x.show(form='ctypes') == 'MYCONST = 16'
    x = ccore.from_db(defs[5])
    assert x._is_typedef
    assert x.show(form='ctypes') == 'foo = CFUNCTYPE(c_int, c_int, c_byte, c_uint, c_void_p)'
    x = ccore.from_db(defs[8])
    assert x._is_typedef
    assert x.show(form='ctypes') == 'foo2 = CFUNCTYPE(POINTER(c_void_p*3), c_int, c_void_p)*2'
    x = ccore.from_db(defs[10])
    assert x._is_struct
    assert x.show(form='ctypes') ==  """struct__mystruct = type('struct__mystruct',(Structure,),{})

struct__mystruct._fields_ = [("I", myinteger),
                             ("tab", c_int*12),
                             ("p", c_ubyte*16),
                             ("s", POINTER(c_short)),
                             ("next", POINTER(struct__mystruct)),
                             ("func", foo),
                             ("bar", struct__bar*2)]"""

def test_format_amoco(configfile,c_header):
    c = conf.Config(configfile)
    conf.config = c
    defs = list(parse(c_header,tag='test'))
    x = ccore.from_db(defs[0])
    assert x._is_macro
    assert x.show(form='amoco') == 'MYCONST = 0x10'
    x = ccore.from_db(defs[5])
    assert x._is_typedef
    assert x.show(form='amoco') == "TypeDefine('foo','P')"
    x = ccore.from_db(defs[8])
    assert x._is_typedef
    assert x.show(form='amoco') == "TypeDefine('foo2','P * 2')"
    x = ccore.from_db(defs[10])
    assert x._is_struct
    assert x.show(form='amoco') == '@StructDefine("""\nmyinteger : I ;comment for field I\ni * 12 : tab ;modern comment for tab\ns * 16 : p ;\nP : s ;\nP : next ;\nfoo : func ;\nstruct__bar * 2 : bar ;\n""")\nclass struct__mystruct(StructFormatter):\n    def __init__(self,data="",offset=0):\n        if data: self.unpack(data,offset)\n    '
