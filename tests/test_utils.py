import pytest
from ccrawl.utils import *

def test_c_type_01():
    t = c_type('int')
    assert t.dim==0
    assert not t.is_ptr
    assert t.lbase=='int'
    assert t.lbfw==0
    assert not t.lconst
    assert not t.lunsigned
    assert len(t.pstack)==0
    assert t.show_base()=='int'
    assert t.show()=='int'
    assert t.show('x')=='int x'

def test_c_type_02():
    t = c_type('unsigned int')
    assert t.dim==0
    assert not t.is_ptr
    assert t.lbase=='int'
    assert t.lbfw==0
    assert not t.lconst
    assert t.lunsigned
    assert len(t.pstack)==0
    assert t.show_base()=='unsigned int'
    assert t.show('x')=='unsigned int x'

def test_c_type_03():
    t = c_type('const unsigned int')
    assert not t.is_ptr
    assert t.lbase=='int'
    assert t.lconst
    assert t.lunsigned
    assert len(t.pstack)==0
    assert t.show('x')=='const unsigned int x'

def test_c_type_04():
    t = c_type('const unsigned char * const')
    assert t.dim==0
    assert t.is_ptr
    assert t.lbase=='char'
    assert t.lconst
    assert t.lunsigned
    assert len(t.pstack)==1
    p = t.pstack[0]
    assert p.is_ptr
    assert p.const
    assert p.p == '*'
    assert str(p)=='*const '
    assert t.show('x')=='const unsigned char *const x'

def test_c_type_05():
    t = c_type('int * (*[2]) [3]')
    assert t.dim==2
    assert t.is_ptr
    assert t.lbase=='int'
    assert not t.lconst
    assert not t.lunsigned
    assert len(t.pstack)==4
    assert t.pstack[0].is_ptr
    assert t.pstack[1].a == 3
    assert t.pstack[2].is_ptr
    assert t.show('x')=='int *(*x[2])[3]'

def test_c_type_06():
    t = c_type('char * (**[4]) (int, struct X*, void (*)(int))')
    assert t.dim==4
    assert t.is_ptr
    assert t.lbase=='char'
    assert len(t.pstack)==4
    f = t.pstack[1]
    assert isinstance(f,fargs)
    assert f.args[1] == ' struct X*'
    assert t.show('funcs')=='char *(**funcs[4])(int, struct X*, void  (*) (int))'

def test_c_type_07():
    t = c_type('void (int, char) [2]')
    assert t.dim==0
    assert not t.is_ptr
    assert t.lbase=='void'
    assert str(t.pstack[0]) == '[2]'
    assert t.pstack[1].f == '(int, char)'

def test_c_type_08():
    t = c_type('struct _mystruct**')
    assert t.is_ptr
    assert t.lbase=='struct _mystruct'
    assert t.pstack[0].p == '**'

def test_c_type_09():
    t = c_type('struct ?_anonymous')
    assert t.show('x')=='struct ?_anonymous x'

def test_c_type_10():
    t = c_type('int #3')
    assert t.lbfw == 3
    assert t.show('x') == 'int x : 3'

def test_cxx_type_11():
    t = cxx_type('class X::Y &')
    assert t.is_ptr
    assert not t.is_method
    assert t.dim==0
    assert t.kw == 'class'
    assert t.ns == 'X::'
    assert t.lbase == 'class X::Y'
    assert t.show_base() == 'Y'
    assert t.show_base(kw=True) == 'class Y'
    assert t.show_base(ns=True) == 'X::Y'
    assert t.show_base(True,True) == 'class X::Y'

def test_cxx_type_12():
    t = cxx_type('struct X& (int, int)')
    assert t.is_method
    assert t.show('f') == 'struct X &f(int, int)'

def test_cxx_type_13():
    t = cxx_type('void () volatile')
    assert t.pstack[0].cvr == 'volatile'
    assert t.is_method

def test_cxx_type_14():
    t = cxx_type('short () &&')
    assert t.pstack[0].cvr == '&&'
    assert t.is_method
    assert t.show('f')=='short f() &&'

def test_cxx_type_15():
    t = cxx_type('void () noexcept')
    assert t.pstack[0].cvr == 'noexcept'
    assert t.is_method
    assert t.show('f')=='void f() noexcept'

def test_cxx_type_16():
    t = cxx_type('struct A::B::C::D')
    assert t.ns == 'A::B::C::'
    assert t.show_base()=='D'


