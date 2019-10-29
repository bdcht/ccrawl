// Templates
//----------
#include <cstddef>
//#include <ostream>

template<typename T>
struct Foo {
  int i;
};

template <typename T>
struct identity
{
    using type = T;
};

template<typename T, int size>
struct sA {
  char tab[size];
  void f(T& t) {}
};

template<class T1, class T2, int I>
class A {};            // primary template

template<class T, int I>
class A<T, T*, I> {};  // #1: partial specialization where T2 is a pointer to T1

template<class T, class T2, int I>
class A<T*, T2, I> {}; // #2: partial specialization where T1 is a pointer

template<class T>
class A<int, T*, 5> {}; // #3: partial specialization where T1 is int, I is 5,
                        //     and T2 is a pointer
template<class X, class T, int I>
class A<X, T*, I> {};   // #4: partial specialization where T2 is a pointer

struct Printer { // generic functor
    std::ostream& os;
    Printer(std::ostream& os) : os(os) {}
    template<typename T>
    void operator()(const T& obj) { os << obj << ' '; } // member template
};
