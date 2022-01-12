import struct
from click import secho
from ccrawl import conf

# default implementation:
def build(obj):
    raise NotImplementedError


def build_gdt(folder_item):
    from zipfile import ZipFile
    from io import BytesIO

    STREAM_MAGIC = 0xACED
    STREAM_VERSION = 0x05
    TC_BLOCKDATA = 0x77
    MAGIC_NUMBER = 0x2E30212634E92C20
    FORMAT_VERSION = 1
    generic_name = b"Archive"
    header = struct.pack(
        ">HHBBQIH7sH7sI",
        STREAM_MAGIC,
        STREAM_VERSION,
        TC_BLOCKDATA,
        0x2A,
        MAGIC_NUMBER,
        FORMAT_VERSION,
        len(generic_name),
        generic_name,
        len(generic_name),
        generic_name,
        0,
    )
    archive = BytesIO()
    with ZipFile(archive, "w") as zfile:
        item = ZipInfo("FOLDER_ITEM")
        zfile.write(item, folder_item)
    length = len(archive.getbuffer())
    return header + struct.pack(">Q", length) + archive.getvalue()


try:
    import ghidra_bridge

    b = ghidra_bridge.GhidraBridge(namespace=locals())
except ImportError:
    secho("ghidra_bridge package not found", fg="red")
except AttributeError:
    secho("ghidra_bridge is not started", fg="red")
except ConnectionRefusedError:
    secho("ghidra_bridge connection error", fg="red")
else:
    # dtm = ghidra.program.model.data.StandAloneDataTypeManager("ccrawl")
    dtm = currentProgram.getDataTypeManager()
    eqt = currentProgram.getEquateTable()
    tr = dtm.startTransaction("ccrawl")
    root = dtm.getRootCategory()
    catp = root.createCategory("ccrawl")
    dtm.endTransaction(tr, True)
    GhidraHandlers = {}

    def declareGhidraHandler(kind, *alt):
        def decorate(f):
            GhidraHandlers[kind] = f
            for other in alt:
                GhidraHandlers[other] = f
            return f

        return decorate

    def build(obj, db):
        n = str(obj.identifier.replace("?_", "").replace(" ", "_"))
        if obj._is_macro:
            s = obj.replace(" ", "")
            e = eqt.getEquate(obj.identifier)
            if e is None:
                if s[-1] == "u":
                    try:
                        value = int(s[:-1], 0)
                    except ValueError:
                        secho("macro conversion error for '%s'" % s[:-1], fg="red")
                    else:
                        e = eqt.createEquate(obj.identifier, value)
            if e is None:
                secho(
                    "macro definition not supported (#define %s '%s')" % (n, s),
                    fg="magenta",
                )
            return e
        x = catp.getDataType(n)
        if x is not None:
            secho("Data type %s already imported" % n, fg="cyan")
            return x
        secho("building data type %s..." % n)
        tr = dtm.startTransaction("build")
        try:
            if obj._is_enum:
                dt = ghidra.program.model.data.EnumDataType(n, 4)
                for k, v in obj.items():
                    dt.add(k, v)
                dt = catp.addDataType(dt, None)
            else:
                x = obj.build(db)
                dt = ctype_to_ghidra(x, dtm)
                if obj._is_func:
                    dt.setName(n)
                if obj._is_typedef:
                    if x.__name__ == "LP_CFunctionType":
                        dt.dataType.setName("proto_%s" % n)
                    dt = ghidra.program.model.data.TypedefDataType(n, dt)
                    dt = catp.addDataType(dt, None)
        except Exception as e:
            secho("ghidra.build exception: %s"%e,fg='red')
        finally:
            dtm.endTransaction(tr, True)
        return dt

    def ctype_to_ghidra(cx, dtm):
        dt = catp.getDataType(cx.__name__)
        if dt is None:
            for cls in cx.mro():
                dt = GhidraHandlers.get(cls.__name__, dt)
            dt = dt(cx, dtm)
        return dt

    @declareGhidraHandler("Array")
    def dt_Array(cx, dtm):
        if conf.DEBUG:
            secho("conversion of %s" % cx, fg="cyan")
        t = ctype_to_ghidra(cx._type_, dtm)
        dt = ghidra.program.model.data.ArrayDataType(t, cx._length_, -1)
        dt = catp.addDataType(dt, None)
        return dt

    @declareGhidraHandler("_Pointer")
    def dt_Pointer(cx, dtm):
        if conf.DEBUG:
            secho("conversion of %s" % cx, fg="cyan")
        t = ctype_to_ghidra(cx._type_, dtm)
        dt = ghidra.program.model.data.PointerDataType(t)
        dt = catp.addDataType(dt, None)
        return dt

    @declareGhidraHandler("Structure")
    def dt_Structure(cx, dtm):
        from ctypes import sizeof

        if conf.DEBUG:
            secho("conversion of %s" % cx, fg="cyan")
        l = sizeof(cx)
        sdt = ghidra.program.model.data.StructureDataType(cx.__name__, 0)
        sdt = catp.addDataType(sdt, None)
        for n, t in cx._fields_:
            dt = ctype_to_ghidra(t, dtm)
            if t.__name__ == "LP_CFunctionType":
                try:
                    dt.dataType.setName("proto_%s" % n)
                except:
                    proto = catp.getDataType("proto_%s" % n)
                    dt =  ghidra.program.model.data.PointerDataType(proto)
            sdt.add(dt, -1, n, "")
        return sdt

    @declareGhidraHandler("Union")
    def dt_Union(cx, dtm):
        from ctypes import sizeof

        if conf.DEBUG:
            secho("conversion of %s" % cx, fg="cyan")
        l = sizeof(cx)
        sdt = ghidra.program.model.data.UnionDataType(cx.__name__, 0)
        sdt = catp.addDataType(sdt, None)
        for n, t in cx._fields_:
            dt = ctype_to_ghidra(t, dtm)
            if t.__name__ == "LP_CFunctionType":
                try:
                    dt.dataType.setName("proto_%s" % n)
                except:
                    proto = catp.getDataType("proto_%s" % n)
                    dt =  ghidra.program.model.data.PointerDataType(proto)
            sdt.add(dt, -1, n, "")
        return sdt

    @declareGhidraHandler("CFunctionType")
    def dt_Function(cx, dtm):
        if conf.DEBUG:
            secho("conversion of %s" % cx, fg="cyan")
        fdt = ghidra.program.model.data.FunctionDefinitionDataType(cx.__name__)
        params = []
        i = 0
        for p in cx._argtypes_:
            dt = ctype_to_ghidra(p, dtm)
            p = ghidra.program.model.data.ParameterDefinitionImpl("p%d" % i, dt, "")
            params.append(p)
        fdt.setArguments(params)
        if cx._restype_ is not None:
            res = ctype_to_ghidra(cx._restype_, dtm)
        else:
            res = ghidra.program.model.data.VoidDataType()
        fdt.setReturnType(res)
        fdt = catp.addDataType(fdt, None)
        return fdt

    @declareGhidraHandler("c_void")
    def dt_void(cx, dtm):
        return ghidra.program.model.data.VoidDataType()

    @declareGhidraHandler("c_void_p", "c_voidp")
    def dt_void_p(cx, dtm):
        v = ghidra.program.model.data.VoidDataType()
        return ghidra.program.model.data.PointerDataType(v)

    @declareGhidraHandler("c_bool")
    def dt_bool(cx, dtm):
        return ghidra.program.model.data.BoolDataType()

    @declareGhidraHandler("c_char")
    def dt_char(cx, dtm):
        return ghidra.program.model.data.CharDataType()

    @declareGhidraHandler("c_char_p")
    def dt_char_p(cx, dtm):
        v = ghidra.program.model.data.CharDataType()
        return ghidra.program.model.data.PointerDataType(v)

    @declareGhidraHandler("c_ubyte", "c_uint8")
    def dt_ubyte(cx, dtm):
        return ghidra.program.model.data.UnsignedCharDataType()

    @declareGhidraHandler("c_byte", "c_int8")
    def dt_byte(cx, dtm):
        return ghidra.program.model.data.ByteDataType()

    @declareGhidraHandler("c_ushort", "c_uint16")
    def dt_ushort(cx, dtm):
        return ghidra.program.model.data.UnsignedShortDataType()

    @declareGhidraHandler("c_short", "c_int16")
    def dt_short(cx, dtm):
        return ghidra.program.model.data.ShortDataType()

    @declareGhidraHandler("c_uint", "c_uint32")
    def dt_uint(cx, dtm):
        return ghidra.program.model.data.UnsignedIntegerDataType()

    @declareGhidraHandler("c_int", "c_int32")
    def dt_int(cx, dtm):
        return ghidra.program.model.data.IntegerDataType()

    @declareGhidraHandler("c_ulong", "c_size_t")
    def dt_ulong(cx, dtm):
        return ghidra.program.model.data.UnsignedLongDataType()

    @declareGhidraHandler("c_long", "c_ssize_t")
    def dt_long(cx, dtm):
        return ghidra.program.model.data.LongDataType()

    @declareGhidraHandler("c_ulonglong", "c_uint64")
    def dt_ulonglong(cx, dtm):
        return ghidra.program.model.data.UnsignedLongLongDataType()

    @declareGhidraHandler("c_longlong", "c_int64")
    def dt_longlong(cx, dtm):
        return ghidra.program.model.data.LongLongDataType()

    @declareGhidraHandler("c_float")
    def dt_float(cx, dtm):
        return ghidra.program.model.data.FloatDataType()

    @declareGhidraHandler("c_double")
    def dt_double(cx, dtm):
        return ghidra.program.model.data.DoubleDataType()

    @declareGhidraHandler("c_longdouble")
    def dt_longdouble(cx, dtm):
        return ghidra.program.model.data.LongDoubleDataType()
