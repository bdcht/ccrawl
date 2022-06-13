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
    if conf.config is None:
        conf.config = conf.Config()
    if conf.config.Ghidra.manager == "program":
        dtm = currentProgram.getDataTypeManager()
        if conf.VERBOSE:
            secho("ghidra_bridge connection with data type manager %s" % dtm, fg="blue")
        tr = dtm.startTransaction("ccrawl")
        root = dtm.getRootCategory()
        catp = root.createCategory(conf.config.Ghidra.category)
        dtm.endTransaction(tr, True)
        if conf.VERBOSE:
            secho("importing types in ccrawl category...", fg="blue")
    else:
        dtm = ghidra.program.model.data.StandAloneDataTypeManager(
            conf.config.Ghidra.category
        )
        if conf.VERBOSE:
            secho(
                "ghidra_bridge connection with standalone data type manager", fg="blue"
            )
        catp = dtm.getRootCategory()

    eqt = currentProgram.getEquateTable()

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
            e = eqt.getEquate(obj.identifier)
            if e is None:
                s = obj.replace(" ", "")
                if s[0] == "(" and s[-1] == ")":
                    s = s[1:-1]
                if s[-1] == "u":
                    try:
                        value = int(s[:-1], 0)
                    except ValueError:
                        secho("macro conversion error for '%s'" % s[:-1], fg="red")
                    else:
                        tr = dtm.startTransaction("equate %s" % obj.identifier)
                        e = eqt.createEquate(obj.identifier, value)
                        dtm.endTransaction(tr, True)
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
        if conf.VERBOSE:
            secho("building data type %s..." % n, nl=False)
        tr = dtm.startTransaction("build")
        try:
            if obj._is_enum:
                I = list(obj.items())
                if len(I) < 256:
                    sz = 1
                elif len(I) < (1 << 16):
                    sz = 2
                else:
                    sz = 4
                dt = ghidra.program.model.data.EnumDataType(n, sz)
                for k, v in obj.items():
                    dt.add(k, v)
                dt = catp.addDataType(dt, None)
            else:
                x = obj.build(db)
                dt = ctype_to_ghidra(x, catp)
                if obj._is_func:
                    dt.setName(n)
                if obj._is_typedef:
                    if x.__name__ == "LP_CFunctionType":
                        dt.dataType.setName("proto_%s" % n)
                    dt = ghidra.program.model.data.TypedefDataType(n, dt)
                    dt = catp.addDataType(dt, None)
        except Exception as e:
            if conf.VERBOSE:
                secho("ghidra.build exception: %s" % e, fg="red")
            dt = None
        else:
            if conf.VERBOSE:
                secho("done.", fg="green")
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
        if conf.DEBUG:
            secho("conversion of %s" % cx, fg="cyan")
        sdt = ghidra.program.model.data.StructureDataType(cx.__name__, 0)
        sdt = catp.addDataType(sdt, None)
        sdt.setToDefaultPacking()
        for f in cx._fields_:
            if len(f) == 3:
                n, t, bfw = f
                # actual "pack" the structure:
                sdt.setExplicitPackingValue(1)
            else:
                n, t = f
                bfw = 0
            dt = ctype_to_ghidra(t, dtm)
            if t.__name__ == "LP_CFunctionType":
                try:
                    dt.dataType.setName("proto_%s" % n)
                except Exception:
                    proto = catp.getDataType("proto_%s" % n)
                    dt = ghidra.program.model.data.PointerDataType(proto)
            if bfw > 0:
                sdt.addBitField(dt, bfw, n, "")
            else:
                sdt.add(dt, -1, n, "")
        sdt.repack()
        return sdt

    @declareGhidraHandler("Union")
    def dt_Union(cx, dtm):
        if conf.DEBUG:
            secho("conversion of %s" % cx, fg="cyan")
        sdt = ghidra.program.model.data.UnionDataType(cx.__name__)
        sdt = catp.addDataType(sdt, None)
        for n, t in cx._fields_:
            dt = ctype_to_ghidra(t, dtm)
            if t.__name__ == "LP_CFunctionType":
                try:
                    dt.dataType.setName("proto_%s" % n)
                except Exception:
                    proto = catp.getDataType("proto_%s" % n)
                    dt = ghidra.program.model.data.PointerDataType(proto)
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
            i += 1
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

    def find_auto_structs(f):
        if isinstance(f, str):
            try:
                f = getGlobalFunctions(f)[0]
            except Exception:
                secho("error: function '%s' not found." % f, fg="red")
                return None
        opt = ghidra.app.decompiler.DecompileOptions()
        ifc = ghidra.app.decompiler.DecompInterface()
        #dut = ghidra.app.decompiler.component.DecompilerUtils
        ifc.setOptions(opt)
        ifc.openProgram(f.getProgram())
        res = ifc.decompileFunction(f, 1000, monitor)
        hf = res.getHighFunction()
        lsm = hf.getLocalSymbolMap()
        Locs = {}
        for n, s in lsm.getNameToSymbolMap().items():
            S = []
            t = s.getDataType()
            if conf.DEBUG:
                secho("\nVariable name & type: '{}' : '{}'".format(n, t), fg="magenta")
            if t.getDescription().startswith("pointer"):
                hv = s.getHighVariable()
                vn0 = hv.getRepresentative()
                todo = [(vn0, 0)]
                done = list(hv.getInstances())
                for vn in done:
                    if vn != vn0:
                        todo.append((vn, 0))
                while len(todo) > 0:
                    if conf.DEBUG:
                        secho("todo: {}".format(todo), fg="green")
                        secho("done: {}".format(done), fg="blue")
                    cur, off0 = todo.pop(0)
                    if cur is None:
                        continue
                    for p in cur.getDescendants():
                        off = off0
                        if conf.DEBUG:
                            secho("  pcode: {}".format(p), fg="magenta")
                        if p.opcode == p.INT_ADD:
                            if p.inputs[1].isConstant():
                                off += getSigned(p.inputs[1])
                                if p.output not in done:
                                    todo.append((p.output, off))
                                    done.append(p.output)
                        elif p.opcode == p.INT_SUB:
                            if p.inputs[1].isConstant():
                                off -= getSigned(p.inputs[1])
                                if p.output not in done:
                                    todo.append((p.output, off))
                                    done.append(p.output)
                        elif p.opcode == p.PTRADD:
                            if p.inputs[1].isConstant() and p.inputs[2].isConstant():
                                off += getSigned(p.inputs[1]) * (
                                    p.inputs[2].getOffset()
                                )
                                if p.output not in done:
                                    todo.append((p.output, off))
                                    done.append(p.output)
                        elif p.opcode == p.PTRSUB:
                            if p.inputs[1].isConstant():
                                off += getSigned(p.inputs[1])
                                if p.output not in done:
                                    todo.append((p.output, off))
                                    done.append(p.output)
                        elif p.opcode == p.LOAD:
                            outdt = getDataTypeTraceForward(p.output)
                            el = (off, outdt.getLength())
                            if el not in S:
                                S.append(el)
                        elif p.opcode == p.STORE:
                            if p.getSlot(cur) == 1:
                                outdt = getDataTypeTraceBackward(p.inputs[2])
                                el = (off, outdt.getLength())
                                if el not in S:
                                    S.append(el)
                        elif p.opcode in (p.CAST, p.MULTIEQUAL, p.COPY):
                            if p.output not in done:
                                todo.append((p.output, off))
                                done.append(p.output)
                        if conf.DEBUG:
                            secho("S = {}".format(S), fg="cyan")
                S.sort()
                Locs[n] = S
        return Locs

    def getSigned(v):
        mask = 0x80 << ((v.getSize() - 1) * 8)
        value = v.getOffset()
        if value & mask:
            value -= 1 << (v.getSize() * 8)
        return value

    def getDataTypeTraceBackward(v):
        res = v.getHigh().getDataType()
        p = v.getDef()
        if (p is not None) and (p.opcode == p.CAST):
            vn = p.getInput(0)
            f = ghidra.program.model.data.MetaDataType.getMostSpecificDataType
            res = f(res, vn.getHigh().getDataType())
        return res

    def getDataTypeTraceForward(v):
        res = v.getHigh().getDataType()
        p = v.getLoneDescend()
        if (p is not None) and (p.opcode == p.CAST):
            vn = p.output
            f = ghidra.program.model.data.MetaDataType.getMostSpecificDataType
            res = f(res, vn.getHigh().getDataType())
        return res

    def do_commit_dtm(t, atm):
        h = ghidra.program.model.data.DataTypeConflictHandler.DEFAULT_HANDLER
        dtm = t.getDataTypeManager()
        atr = atm.startTransaction("commit to archive")
        dtr = dtm.startTransaction("update dt synch time")
        try:
            print("commit '%s' " % (t.getName()), end="")
            at = atm.resolve(t, h)
            if at.name != t.name:
                at.setName(t.name)
            if at.getDescription() != t.getDescription():
                at.setDescrption(t.getDescription())
        except Exception:
            secho("error!", fg="red")
        else:
            secho("✔️", fg="green")
        dtm.endTransaction(dtr, True)
        atm.endTransaction(atr, True)

    def commit_local_to_gdt(name):
        dtmservice = ghidra.app.services.DataTypeManagerService
        dtm = currentProgram.getDataTypeManager()
        Alldtm = {}
        for adtm in state.getTool().getService(dtmservice).getDataTypeManagers():
            Alldtm[adtm.name] = adtm
        sadtm = None
        sa = None
        for a in dtm.sourceArchives:
            if a.name == name:
                sa = a
                sadtm = Alldtm.get(name, None)
                break
        if sa and sadtm:
            for dt in dtm.getDataTypes(sa):
                info = ghidra.app.plugin.core.datamgr.DataTypeSyncInfo(dt, sadtm)
                if info.canCommit():
                    do_commit_dtm(dt, sadtm)

    def dt_apply_recursive(dt, address):
        dtm.findDataTypes
