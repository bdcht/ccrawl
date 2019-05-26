// see all AST with: clang -Xclang -ast-dump -fsyntax-only samples/classes.hpp
//
#include <cstddef>
#include <string>
#include <vector>

// Basic Classes:
//---------------
//

struct oldstruct {
  int  *X;
  char c;
};

struct oldunion {
  int  Y;
  char q;
};

struct newstruct {
  int  *X;
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
  MyClass(int x) : field(x) {};
  ~MyClass() {};
  int method(wchar_t);
  virtual void vmethod() const = 0;
  virtual int  vmethod(int);
  virtual char vmethod(int,MyClass&);
public:
  int *pubfield;
  const int constmeth(char);
  virtual void pmethod();
protected:
  static const int static_field;
  static int static_method();
};

class S {
protected:
    int *d1; // non-static data member
    int a[10] = {1,2}; // non-static data member with initializer (C++11)
    static const int d2 = 1; // static data member with initializer
public:
    virtual void f1(int) = 0; // pure virtual member function
    std::string d3, *d4, f2(int); // two data members and a member function
    enum {NORTH, SOUTH, EAST, WEST};
    struct NestedS {
        std::string s;
        virtual void f(int);
    } d5, *d6;
private:
    typedef NestedS value_type, *pointer_type;
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
