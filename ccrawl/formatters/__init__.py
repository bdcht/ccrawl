formats = ['raw', 'C', 'ctypes', 'amoco']

from .raw           import  ccore_raw
from .C             import  (cTypedef_C,
                            cMacro_C,
                            cFunc_C,
                            cEnum_C,
                            cStruct_C,
                            cUnion_C,
                            cClass_C,
                            cTemplate_C)
from .ctypes_       import  (cTypedef_ctypes,
                            cMacro_ctypes,
                            cFunc_ctypes,
                            cEnum_ctypes,
                            cStruct_ctypes,
                            cUnion_ctypes,
                            cClass_ctypes)
from .amoco         import  (cTypedef_amoco,
                            cMacro_amoco,
                            cFunc_amoco,
                            cEnum_amoco,
                            cStruct_amoco,
                            cUnion_amoco)
from .volatility    import  (cTypedef_volatility,
                            cEnum_volatility,
                            cMacro_volatility,
                            cFunc_volatility,
                            cStruct_volatility,
                            cUnion_volatility)
#from .protobuf import *
#from .kaitaistruct import *
