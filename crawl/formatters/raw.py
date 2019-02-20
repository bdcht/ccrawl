import pprint

# default raw formatter:
#------------------------------------------------------------------------------

def ccore_raw(obj,db,tag,recursive):
    return '{}:\n{}'.format(obj.identifier,pprint.pformat(obj))

default = ccore_raw

