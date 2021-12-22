import pytest
from ccrawl.core import ccore
from ccrawl.parser import *

def test_clang_cindex(configfile):
    c = conf.Config(configfile)
    c.Terminal.quiet = True
    c.Terminal.timer = False
    c.Collect.strict = False
    c.Collect.cxx    = False
    conf.config = c
    try:
        index = Index.create()
    except:
        raise AssertionError
    assert index is not None
    assert hasattr(index,'parse')

def test_clang_parser(configfile,c_empty):
    c = conf.Config(configfile)
    c.Terminal.quiet = True
    c.Terminal.timer = False
    c.Collect.strict = False
    c.Collect.cxx    = False
    conf.config = c
    index = Index.create()
    options  = TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    options |= TranslationUnit.PARSE_INCOMPLETE
    options |= TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
    args = ['-ferror-limit=0','-fparse-all-comments']
    tu = index.parse(c_empty,args,[],options)

def test_parser_c(configfile,c_header):
    c = conf.Config(configfile)
    c.Terminal.quiet = True
    c.Terminal.timer = False
    c.Collect.strict = False
    c.Collect.cxx    = False
    conf.config = c
    defs = list(parse(c_header,tag='test'))
    assert defs[0]['cls'] == 'cMacro'
    assert defs[0]['id']  == 'MYCONST'
    assert defs[0]['tag'] == 'test'
    assert defs[0]['val'] == ' 0x10'
    x = ccore.from_db(defs[5])
    assert x._is_typedef
    assert str(x)=='int (*)(int, char, unsigned int, void *)'

def test_parser_cxx(configfile,cxx_myclass):
    c = conf.Config(configfile)
    c.Terminal.quiet = True
    c.Terminal.timer = False
    c.Collect.strict = False
    c.Collect.cxx    = True
    conf.config = c
    defs = list(parse_string(cxx_myclass))
    assert len(defs)==1
    x = ccore.from_db(defs[0])
    assert x._is_class
    assert len(x)==11
    assert x[4] == (('', 'void (int)'),
                    ('_ZN7MyClassC1Ei', 'MyClass'),
                    ('PUBLIC', None))
