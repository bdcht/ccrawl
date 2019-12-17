// testing parsing c++ header without hpp suffix...
// testing class layout as illustrated in cxxabi (http://refspecs.linuxbase.org/cxxabi-1.83.html)
//

namespace myNS {

class A1 { int a; };
class A2 { int aa; virtual void f(); };
class V1 : public A1, public A2 { int v; };
// A2 is primary base of V1, A1 is non-polymorphic
class B1 { int b; };
class B2 { int bb; };
class V2 : public B1, public B2, public virtual V1 { int vv; };
// V2 has no primary base, V1 is secondary base
class V3 {virtual void g(); };
class C1 : public virtual V1 { int c; };
// C1 has no primary base, V1 is secondary base
class C2 : public virtual V3, virtual V2 { int cc; };
// C2 has V3 primary (nearly-empty virtual) base, V2 is secondary base
class X1 { int x; };
class C3 : public X1 { int ccc; };
class D : public C1, public C2, public C3 { int d;  };
// C1 is primary base, C2 is secondary base, C3 is non-polymorphic
//
}
