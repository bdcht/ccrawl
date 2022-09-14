from ccrawl.utils import struct_letters, c_type, cxx_type
from ccrawl.db import where
from ccrawl.core import ccore

try:
    from grandalf.graphs import Graph,Vertex,Edge
    from grandalf.layouts import SugiyamaLayout
    has_graph = True

    class Node(Vertex):
        """A Node is a grandalf.Vertex equipped with a label property
           an improved __repr__ method that displays the Vertex's data
           and type of data (a ccore instance or a str) and a loc
           method that reports its index within the graph (unless its
           not yet part of a graph.)
        """

        @property
        def label(self):
            if self.data:
                if hasattr(self.data,'identifier'):
                    return self.data.identifier
                else:
                    return self.data
            return None

        def is_ccore(self):
            return (ccore in self.data.__class__.mro())

        def loc(self,pre=""):
            i = self.index
            if i is None:
                si = hex(id(self))
            else:
                si = "%s%d"%(pre,i)
            return si

        def __repr__(self):
            i = self.loc("v")
            n = self.label
            if n is None:
                return "<Node %s, data: None>"%i
            else:
                t = self.data.__class__.__name__
                return "<Node %s, data: '%s' (%s)>"%(i,n,t)


    class Link(Edge):
        """A Link is a grandalf.Edge equipped with a label property
           and an improved __repr__ method.
        """

        def __init__(self,x,y,data=None):
            super().__init__(x,y,1.0,data)

        @property
        def label(self):
            return self.data or ""

        def __repr__(self):
            n0, n1 = [v.loc("v") for v in self.v]
            return "<Link @ %s, %s -> %s>"%(hex(id(self)),n0,n1)


    class CGraph(Graph):
        """A CGraph is a grandalf.Graph equipped with a
           an improved __repr__ method.
        """

        def __repr__(self):
            return "<CGraph @ %s, C: %s>"%(hex(id(self)),str([g.order() for g in self.C]))


except ImportError:
    has_graph = False


def build(obj,db,V=None,g=None):
    """
    This function takes a ccrawl.core object and a db.Proxy and returns
    the dependency graph of this object as a CGraph instance. 
    
    Optional arguments V and g allow to extend the current dict of Node (V)
    and a CGraph (g) from another given object.
    """
    if has_graph:
        obj.unfold(db)
        if V is None:
            V = {}
        if g is None:
            g = CGraph()
        do_graph(obj,V,g)
    return g

def do_graph(obj,V,g):
    """
    This function takes an unfolded ccrawl.core object, a dict V of Nodes
    (acting a the current cache set of Nodes created so far for this graph),
    and a CGraph instance g.

    It "fills" g with new Link edges (and thus new Nodes as well) by walking
    the given cStruct/cUnion/cTypedef object and instanciating new Nodes and
    Links based on the corresponding subtypes and names.
    """
    # get/add Node obj to V dict:
    if obj.identifier in V:
        v = V[obj.identifier]
    else:
        v = Node(obj)
        V[obj.identifier] = v
    if obj._is_struct or obj._is_union:
        # we walk the struct/union fields to
        # set the edge's data from the field's accessor
        def _walk(o):
            for (t,n,c) in o:
                ct = c_type(t)
                elt = ct.lbase
                # we ignore raw C types (int, float, ...)
                if elt in o.subtypes:
                    # get the ccore oect for this type:
                    x = o.subtypes[elt]
                    yield (elt,x,ct.show_ptr(n))
    else:
        # otherwise we walk from the subtypes:
        def _walk(o):
            for elt,x in o.subtypes.items():
                # (ignoring raw C types also)
                if elt in o.subtypes:
                    if o._is_typedef:
                        ct = c_type(o)
                        l = ct.show_ptr("")
                    else:
                        l = None
                    x = o.subtypes[elt]
                    yield (elt,x,l)

    for (elt,x,accessor) in _walk(obj):
        # get/create destination node:
        if elt in V:
            vd = V[elt]
        else:
            vd = Node(x)
            if vd.data is None:
                # the type of this field was not found in database
                # we use its literal as vertex data...
                vd.data = elt
        # create link
        e = Link(v,vd,data=accessor)
        # add link to graph
        g.add_edge(e)
        # if not done already, add node and recurse if possible:
        if elt not in V:
            V[elt] = vd
            if x is not None:
                assert vd.data==x
                assert x.identifier==elt
                do_graph(x,V,g)

def get_typegraph_cycles_params(g,r=None):
    """
    For a given CGraph g, returns the "cycles" found in this graph as
    a dict where the key is a root Node for a cycle, and the value is
    a list of cycles.
    Each cycle is defined as a tuple of "accessors" that correspond
    to all Links' data values that returns back to the root Node. 
    """
    X = {}
    for gc in g.C:
        L = gc.get_scs_with_feedback()
        for l in L:
            sz = len(l)
            if sz>1:
                # the strongly connect component is non trivial...
                # lets compute its cycles:
                p = get_scs_params(l)
                if p is not None:
                    X.update(p)
    return X

from itertools import tee
def get_scs_params(l):
    """
    For a given list of Nodes that form a strongly connected component
    of a graph, compute all cycles from the initial (root) Node.
    """
    def pairwise(it):
        a,b = tee(it)
        next(b,None)
        return zip(a,b)
    params = set()
    if len(l)>0:
        v0 = l[0]
        D = v0.c.dijkstra(v0,+1,subset=l)
        for vd,d in D.items():
            if d>0.0:
                P = []
                p = v0.c.path(v0,vd,+1) + v0.c.path(vd,v0,+1)[1:]
                assert len(p)>2
                for x,y in pairwise(p):
                    e = x.e_to(y)
                    P.append(e.data or '')
                params.add(tuple(P))
    return {v0: params}

def get_cycles(obj,db,psize=4):
    """
    For a given ccrawl.core object, compute its dependency graph "cycles".
    """
    g = build(obj,db)
    X = get_typegraph_cycles_params(g)
    R = {}
    for v0,params in X.items():
        RL = []
        for P in params:
            RL.append(get_cycle_offsets(v0,db,P,psize))
        R[v0.data.identifier] = RL
    return R

def parse_accessor(s):
    i = s.rfind("[")
    if i>0:
        a,s = s[i:],s[:i]
        a = int(a[1:-1])
    else:
        a = 0
    if s.startswith("*"):
        i = s.rindex("*")+1
        p,s = s[:i],s[i:]
    else:
        p = ''
        i = 0
    return (p,s,a)


from ccrawl.ext import amoco
def get_cycle_offsets(node,db,P,psize):
    """
    For a given cycle P, associated to a root node, return
    the list of (offset,name) or deref operator '*' that correspond to
    this cycle.
    """
    def offset_of(obj,db,el,psize):
        i = obj.index_of(el)
        if db.rdb:
            _id = db.rdb.db["nodes"].find_one({"id": obj.identifier})["_id"]
            col = db.rdb.db["structs_ptr%d"%(psize*8)]
            j = col.find_one({"_id": _id})
            if j and i is not None:
                return j["offsets"][i]
        # otherwise we need to build the struct:
        ax = amoco.build(obj,db)()
        return ax.offsets(psize)[i]
    r = []
    cur = node
    for el in P:
       p,s,a = parse_accessor(el)
       if s:
           i = offset_of(cur.data,db,s,psize)
           r.append((i[0],s))
       r.extend(list(p))
       for e in cur.e_out():
           if e.data==el:
               cur = e.v[1]
    return r
