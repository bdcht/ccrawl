#include "wonza.hpp"
#include <iostream>

union newunion S::NestedS::f(int a) {
    union newunion u;
    u.Y = a;
    return u;
}

const int MyClass::constmeth(char c) {
   return 0xAA;
}

int MyClass::vmethod(int x) {
   return this->static_method()+x;
}

int Badabang::foo(int i = 0) {
    return i+1;
}

int T::fa(int x) {
    return x + this->privT + this->d2;
}

int main(int argc, char* argv[]) {
    myint i;
    newstruct n;
    MyClass x(1);
    T t;
    Badabang w;

    i = 100;
    n.X = &i;
    x.pubfield = n.X;
    i = x.constmeth('A');
    i += x.vmethod(-1);
    t.setpriv(99);
    std::cout << "stats:";
    std::cout << "sizeof(std::string)=" << sizeof(std::string);
    return i+w.foo();
}
