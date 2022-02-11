import pprint

__all__ = ["ccore_raw"]

# default raw formatter:
# ------------------------------------------------------------------------------


def ccore_raw(obj, db, recursive):
    return "{}:\n{}".format(obj.identifier, pprint.pformat(obj))


default = ccore_raw
