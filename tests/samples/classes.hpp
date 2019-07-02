// see all AST with: clang -Xclang -ast-dump -fsyntax-only samples/classes.hpp
//
//#include <cstddef>
//#include <string>
//#include <vector>

// Basic Classes:
//---------------
//
//
namespace std {
    template<int> class vector;
}

struct oldstruct {
  myint  *X;
  char c;
};

union oldunion {
  int  Y;
  char q;
};

struct newstruct {
  myint  *X;
protected:
  char c;
  void meth(void);
};

union newunion {
  int  *Y;
protected:
  char c;
  void meth(void);
  char meth(char);
};

//// MyClass comment
class MyClass
{
  int field;
  int method(wchar_t);
  virtual char vmethod(int,MyClass&);
public:
  myint *pubfield;
  MyClass(int x) : field(x) {};
  ~MyClass() {};
  virtual int  vmethod(int);
  const int constmeth(char);
  virtual void pmethod();
protected:
  static const int static_field;
  static int static_method();
};

class S {
public:
    int *d1; // non-static data member
    virtual int fa(int) = 0; // pure virtual member function
    struct NestedS {
        std::string s;
        virtual void f(int);
    } d5, *d6;
protected:
    int a[10] = {1,2}; // non-static data member with initializer (C++11)
    static const int d2 = 1; // static data member with initializer
    std::string d3, *d4, f2(int); // two data members and a member function
    enum {NORTH, SOUTH, EAST, WEST};
};

class T : S {
public:
     virtual int fa(int);
};

class M {
    std::size_t C;
    std::vector<int> data;
 public:
    M(std::size_t R, std::size_t C) : C(C), data(R*C) {} // constructor definition 
    int operator()(size_t r, size_t c) const { // member function definition
        return data[r*C+c];
    }
    int& operator()(size_t r, size_t c) {  // another member function definition
        return data[r*C+c];
    }
};
