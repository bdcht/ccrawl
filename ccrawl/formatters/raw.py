import pprint

# default raw formatter:
#------------------------------------------------------------------------------

def ccore_raw(obj,db,recursive):
    return '{}:\n{}'.format(obj.identifier,pprint.pformat(obj))

default = ccore_raw

