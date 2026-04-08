from ccrawl import conf
from ccrawl.core import ccore, cStruct
from ccrawl.utils import struct_letters, c_type, cxx_type, fargs, pp
from click import secho

try:
    from scapy import fields
    from scapy import packet
except ImportError:
    secho("scapy package not found", fg="red")
    
    def build(t, db, _bstack=[])
        raise NotImplementedError

else:

    from collections import defaultdict, ordereddict

    def default_handler(sf,pkt,ctx):
        name = sf.__class__.__name__
        if name.startswith('X'): name=name[1:]
        if name.startswith('LE'): name=name[2:]
        t = S_to_C.get(sf.__class__.__name__,'int')
        n = sf.name
        c = ''
        return [(t,n,c)]

    ScapyHandlers = defaultdict(default_handler)

    S_to_C = {
            'LenField': 'usize_t',
            'ByteField': 'unsigned char',
            'SignedByteField': 'char',
            'IntField': 'unsigned int',
            'SignedIntField': 'int',
            'ShortField': 'unsigned short int',
            'SignedShortField': 'short int',
            'LongField': 'unsigned long long',
            'SignedLongField': 'long long',
            'IEEEFloatField': 'float',
            'IEEEDoubleField': 'double',
    }
    stru_to_c = {'B': 'unsigned char',
                 'H': 'unsigned short',
                 'I': 'unsigned int',
                 'L': 'unsigned long',
                 'Q': 'unsigned long long'}
    size_to_c = { 1 : 'unsigned char',
                  2 : 'unsigned short',
                  4 : 'unsigned int',
                  8 : 'unsigned long long'}

    def declareHandler(fld):
        if isinstance(fld,fields.Field):
            #arg is a field instance
            sfname = fld.__class__.__name__
        else:
            #arg is a field metaclass
            sfname = fld.__name__
        def decorate(f):
            ScapyHandlers[sfname] = f
            return f
        return decorate

    @declareHandler(fields.NBytesField)
    @declareHandler(fields.XNBytesField)
    @declareHandler(fields.StrFixedLenField)
    @declareHandler(fields.StrLenField)
    @declareHandler(fields.XStrFixedLenField)
    @declareHandler(fields.XStrLenField)
    @declareHandler(fields.MACField)
    @declareHandler(fields.IPField)
    @declareHandler(fields.IP6Field)
    @declareHandler(fields.TrailerField)
    @declareHandler(fields.PadField)
    def scapy_unsigned_char_array(sf,pkt,ctx):
        return [('unsigned char[%d]'%sf.sz, sf.name, '')]

    @declareHandler(fields.CharEnumField)
    @declareHandler(fields.ByteEnumField)
    @declareHandler(fields.ShortEnumField)
    @declareHandler(fields.IntEnumField)
    @declareHandler(fields.LongEnumField)
    def scapy_sz_to_c(sf,pkt,ctx):
        t = size_to_c.get(sf.sz,'?')
        return [(t, sf.name, '')]

    @declareHandler(fields.FieldLenField)
    def scapy_LenField(sf,pkt,ctx):
        "A field that is an indicator of length of another field"
        t = stru_to_c.get(sf.fmt,'unsigned int')
        c = []
        if sf.length_of:
            c.append("length of %s"%sf.length_of)
        if sf.count_of:
            c.append("count of %s"%sf.count_of)
        return[(t, sf.name, "; ".join(c))]

    @declareHandler(fields.BitLenField)
    @declareHandler(fields.BitField)
    @declareHandler(fields.BitLenEnumField)
    @declareHandler(fields.BitEnumField)
    @declareHandler(fields.XBitField)
    def scapy_BitField(sf,pkt,ctx):
        "A field that is equivalent to a C bitfield"
        r = 1 if sf.size%8 else 0 
        bsz = max(abs(sf.tot_size),abs(sf.end_tot_size))
        l = bsz+r
        t = size_to_c.get(l,'?')
        t += "#%d"%sf.size
        return[(t, sf.name, ''))]

    @declareHandler(fields.FieldListField)
    def scapy_ListField(sf,pkt,ctx):
        "A field that is an array of another field"
        assert isinstance(sf.field,fields.Field)
        inner = ScapyHandlers[sf.field.__class__.__name__](sf.field,pkt,ctx)
        t, n, c = inner[0]
        ct = c_type(t)
        ct.pstack.append(arr(sf.sz))
        return[(ct.show(), n, c)]

    @declareHandler(fields.PacketField)
    def scapy_PacketField(sf,pkt,ctx):
        "A field that is described by a packet (ie structured type)"
        assert isinstance(sf.field,fields.Field)
        inner = ScapyHandlers[sf.field.__class__.__name__](sf.field,pkt,ctx)
        t, n, c = inner[0]
        ct = c_type(t)
        ct.pstack.append(arr(sf.sz))
        return[(ct.show(), n, c)]

    @declareHandler(fields.PacketListField)
    def scapy_PacketList(sf,pkt,ctx):
        "A field that is described by a list of packets"
        assert sf.holds_packets
        P = [to_ccore(p) for p in getattr(pkt,sf.name)]
        if len(set((obj.identifier for obj in P)))==1:
            ctx[P[0].identifier] = P[0]
            return [("%s[%d]"%(P[0].identifier,len(P)), sf.name, '')]
        else:
            L = []
            for i,p in enumerate(P):
                ctx[p.identifier] = p
                L.append((p.identifier, "%s_%d"%(sf.name,i), ''))
            return L

    @declareHandler(fields.ConditionalField)
    def scapy_conditional(sf,pkt,ctx):
        return ScapyHandlers[sf.fld](sf.fld,pkt,ctx)


    def to_ccore(sx, identifier="", **kargs):
        """
        Translate a scapy Packet type to a ccrawl.core.cStruct object,
        thus allowing to export this object to any other supported format.
        """
        ctx = kargs.get("ctx", OrderedDict(struct_letters))
        assert isinstance(sx,packet.Packet)
        ctx = OrderedDict()
        obj = cStruct()
        obj.identifier = identifier or sx.__class__.__name__
        for f in sx.fields_desc:
            obj.append(ScapyHandlers[f.__class__.__name__](f,sx,ctx))
        obj.subtypes = ctx
        return obj

