from ccrawl.utils import *
from ccrawl.ext.ctypes_ import build
from ctypes import sizeof

# kaitaistruct formatters:
#------------------------------------------------------------------------------

to_kaitai = {
        'char': 's1',
        'short': 's2',
        'int': 's4',
        'long': 's4',
        'long long': 's8',
        'float': 'f4',
        'double': 'f8'}

def cMacro_kaitaistruct(obj,db,recursive):
    pass

def cFunc_kaitaistruct(obj,db,recursive):
    pass

def ctype_to_kaitaistruct(t):
    b = t.lbase
    if b not in to_kaitai:
        res = b.replace('?_','').replace(' ','_')
    else:
        res = to_kaitai[b]
        if t.lunsigned: res='u'+res
    if t.is_ptr: res = 'u8'
    res = 'type : %s'%res
    if t.dim>0:
        res += '\nrepeat: expr\nrepeat-expr: %d'%t.dim
    return res

