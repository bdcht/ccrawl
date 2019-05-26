// testing parsing c++ header without hpp suffix...
// testing class layout as illustrated in cxxabi (http://refspecs.linuxbase.org/cxxabi-1.83.html)
//

namespace myNS {

class A1 { int i; };
class A2 { int i; virtual void f(); };
class V1 : public A1, public A2 { int i; };
// A2 is primary base of V1, A1 is non-polymorphic
class B1 { int i; };
class B2 { int i; };
class V2 : public B1, public B2, public virtual V1 { int i; };
// V2 has no primary base, V1 is secondary base
class V3 {virtual void g(); };
class C1 : public virtual V1 { int i; };
// C1 has no primary base, V1 is secondary base
class C2 : public virtual V3, virtual V2 { int i; };
// C2 has V3 primary (nearly-empty virtual) base, V2 is secondary base
class X1 { int i; };
class C3 : public X1 { int i; };
class D : public C1, public C2, public C3 { int i;  };
// C1 is primary base, C2 is secondary base, C3 is non-polymorphic
//
}
