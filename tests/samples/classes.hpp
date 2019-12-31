// see all AST with: clang -Xclang -ast-dump -fsyntax-only samples/classes.hpp
//
//#include <cstddef>
//#include <string>
//#include <vector>

typedef int myint;

// Basic Classes:
//---------------
//
//
//namespace std {
//    template<int> class vector;
//}

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
private:
  newstruct *next;
};

union newunion {
  int  Y;
protected:
  char c;
  void meth(void);
  char meth(char);
};

//// MyClass comment
class MyClass
{
  int field;
  newstruct method(wchar_t w) {
    newstruct x;
    myint z;
    z = (myint) w;
    x.X = &z;
    return x;
  };
  virtual char vmethod(int a,MyClass &b) {
    return 'c' & char((a+*(b.pubfield))&0xff);
  };
public:
  myint *pubfield;
  MyClass(int x) : field(x) {};
  ~MyClass() {};
  virtual int  vmethod(int);
  const int constmeth(char);
  virtual void pmethod() {};
protected:
  static const int static_field = 10;
  static int static_method() { return static_field; };
};

class S {
public:
    struct oldstruct *d1; // non-static data member
    virtual int fa(int) = 0; // pure virtual member function
    struct NestedS {
        std::string s = "abc";
        virtual union newunion f(int);
    } d5, *d6;
protected:
    int a[10] = {1,2}; // non-static data member with initializer (C++11)
    static const int d2 = 1; // static data member with initializer
    std::string d3, *d4, f2(int); // two data members and a member function
    enum {NORTH, SOUTH, EAST, WEST} e;
private:
    int privS;
    void setpriv(int x) { privS = x; };
};

class T : S {
private:
    int privT;
public:
     int* X[2];
     T() {
        d3 = d5.s;
        d4 = &d3;
        d6 = &d5;
     };
     virtual int fa(int) override;
     void setpriv(int x) {
        privT = x + d6->f(d2).Y;
        X[0] = &(a[1]);
        X[1] = &(a[0]);
     };
};

class Scv {
    int mf1(); // non-static member function declaration
    void mf2() volatile, mf3() &&; // can be cv-qualified and reference-qualified
    int mf4() const { return data; } // can be defined inline
    virtual void mf5() final; // can be virtual, can use final/override
    Scv() : data(12) {} // constructors are member functions too
    int data;
};

class M : T {
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
