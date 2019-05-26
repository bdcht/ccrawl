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
};

int main()
{
    A a;
    B b;
    C c;
//  D d; // compile error
    E e;
//  F f; // compile error
}
