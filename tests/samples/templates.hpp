// Templates
//----------
//#include <cstddef>
//#include <ostream>

template<typename T>
struct Foo {
  int i;
  T t;
};

template <typename T>
struct identity
{
    using type = T;
    type v;
};

template<typename T, int size = 8>
struct sA {
  char tab[size];
  void f(T& t) {}
};

template<class T1, class T2, int I>
class A {
  T1 t1;
  T2 t2;
  char  b[I];
};

// #1: partial specialization where T2 is a pointer to T1
template<class T, int I>
class A<T, T*, I> {
};

// #1: partial specialization one T1 is provided
template<class T1>
class A<T1*, Foo<char>, 8> {};

template<>
class A<int, sA<char>, (2<<3) > {};

struct Printer { // generic functor
    std::ostream& os;
    Printer(std::ostream& os) : os(os) {}
    template<typename T>
    void operator()(const T& obj) { os << obj << ' '; } // member template
};

namespace bars {

    template<typename T>
    class Bar {
     T t;
    };
    
    template<>
    class Bar<void> {
        sA<int> t;
    };
    
    template<typename T1, typename T2 = Foo<char>>
    class Bar2 {
     T1 t1;
     T2 t2;
     sA<Foo<T2>, (100>>2) > sa;
    };

};

template <typename T0>                         // Level 0: T0 is type-parameter-0-0
struct Level1 {
    template <template <typename> typename T1> // Level 1: T1 is STILL type-parameter-1-0
    struct Level2 {
        // T1 is not a type (like int). 
        // T1 is a template (like std::vector).
        T1<T0> data; 
        template <template <typename> typename T2>
        T0 func(T2<T1<T0>> arg) {}
    };
    Level2<Foo> l2foo;
};

using L1 = struct Level1<bars::Bar<void>>;

typedef L1::Level2<bars::Bar> L2;

class l {
  L2 v;
};

