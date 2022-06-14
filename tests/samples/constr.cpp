#include "classes.hpp"

using namespace NS;

struct A
{
    int x;
    A(int x = 1): x(x) {} // user-defined default constructor
};

struct B: A
{
    // B::B() is implicitly-defined, calls A::A()
};

struct C
{
    A a;
    // C::C() is implicitly-defined, calls A::A()
};

struct D: A
{
    D(int y): A(y) {}
    // D::D() is not declared because another constructor exists
};

struct E: A
{
    E(int y): A(y) {}
    E() = default; // explicitly defaulted, calls A::A()
};

struct F
{
    int& ref; // reference member
    const int c; // const member
    // F::F() is implicitly defined as deleted
private:
    Scv z;
};


void newstruct::meth(void) {};

void newunion::meth(void) {};

char newunion::meth(char) {
return 'A';
};

int MyClass::method(wchar_t) {
return 0;
};

int MyClass::vmethod(int x) {
    this->field = x;
    return x+1;
};

char MyClass::vmethod(int x, MyClass &y) {
    return 'A';
}

const int MyClass::constmeth(char x) {
    return 100+(int)x;
}

void MyClass::pmethod() {};
int MyClass::static_method() {
return 0;
};

void S::NestedS::f(int x) {
    x+1;
}
int T::fa(int x) {
    return (this->a[1] + x);
}

int f(C c) {
    struct newstruct ns;
    MyClass my(10);
    T s;
    my.vmethod(3);
    ns.X = my.pubfield;
    return *(ns.X) + s.fa(5);
}

int main()
{
    A a;
    B b;
    C c;
//  D d; // compile error
    E e(0);
//  F f; // compile error
    c.a.x += a.x + b.x;

    e.x += f(c);
    return (e.x + c.a.x);
}

