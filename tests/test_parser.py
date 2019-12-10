import pytest
from ccrawl.parser import *

def test_clang_cindex(configfile):
    print(clang.cindex.Config.library_file)
    c = conf.Config(configfile)
    c.Terminal.quiet = True
    c.Terminal.timer = False
    c.Collect.strict = False
    c.Collect.cxx    = False
    conf.config = c
    clang.cindex.Config.library_file = c.Collect.lib
    assert clang.cindex.Config.library_file is not None
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

def test_parser_01(configfile,c_header):
    c = conf.Config(configfile)
    c.Terminal.quiet = True
    c.Terminal.timer = False
    c.Collect.strict = False
    c.Collect.cxx    = False
    conf.config = c
    defs = parse(c_header,tag='test')
