import pytest
from ccrawl.core import *

def test_ccore():
    x = ccore()
    assert not x._is_typedef
    assert not x._is_struct
    assert not x._is_union
    assert not x._is_enum
    assert not x._is_macro
    assert not x._is_func
    assert not x._is_class
    assert not x._is_template
    assert not x._is_namespace
    assert x.formatter is None
    y = x.getcls('cStruct')
    assert y._is_struct

def test_from_db_1(db_doc1):
    x = ccore.from_db(data=db_doc1)
    assert x._is_typedef
    assert x.identifier == 'xxx'
    assert x.subtypes is None
    assert str(x)=='int'
    x.unfold(None)
    assert type(x.subtypes).__name__ == 'OrderedDict'

def test_from_db_2(db_doc2):
    x = ccore.from_db(data=db_doc2[0])
    assert x._is_struct
    assert x.identifier == 'struct X'
    assert x.subtypes is None
    class DB(object):
        def get(self,id):
            if id=='yyyy':
                return db_doc2[1]
            else:
                raise NotImplementedError
    x.unfold(DB())
    assert 'yyyy' in x.subtypes
    y = x.subtypes['yyyy']
    assert y._is_typedef
