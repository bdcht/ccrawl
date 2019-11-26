#include <iostream>
using namespace std;

class Grandparent {
 public:
  virtual void grandparent_foo() {}
  int grandparent_data;
};

class Parent1 : virtual public Grandparent {
 public:
  virtual void parent1_foo() {}
  int parent1_data;
};

class Parent2 : virtual public Grandparent {
 public:
  virtual void parent2_foo() {}
  int parent2_data;
};

class Child : public Parent1, public Parent2 {
 public:
  virtual void child_foo() {}
  int child_data;
};

struct A {
  int a;
};

struct B {
  int b;
};

struct AB : A, B {
  int ab;
};

struct C : A, B {
  int c;
  virtual void f() {this->c = this->a + this->b; };
};

struct D : virtual A, virtual B {
  int d;
  virtual void g() {this->d = this->a + this->b; };
};

struct E : virtual B, virtual A {
  int e;
  virtual void h() {this->e = this->a + this->b; };
};

struct F : D, E {
  int f;
  virtual void i() {this->f = this->d + this->e; };
};

struct G : virtual A, B {
  int g;
};

struct H : B, virtual A {
  int h;
};

struct I : G, H {
  int i;
  virtual void j() {};
};

int main() {
  Grandparent gp;
  Parent1 dad;
  Parent2 mom;
  Child child;
  AB ab;
  C c;
  D d;
  E e;
  F f;
  G g;
  H h;
  I i;

  c.a = 1;
  c.b = 2;
  c.f();
  f.a = 5;
  f.b = 6;
  f.g();
  f.h();
  f.e = 20;
  f.i();

  i.a = 0x100;
  ((G*)&i)->b = 0x101;
  i.g = 0x102;
  ((H*)&i)->b = 0x103;
  i.h = 0x104;
  i.i = 0x105;

  gp.grandparent_data = c.c;
  dad.grandparent_data = 2;
  dad.parent1_data = 3;
  mom.grandparent_data = 4;
  mom.parent2_data = 5;
  child.grandparent_data = 6;
  child.parent1_data = 7;
  child.parent2_data = 8;
  child.child_data = 9;
  ((Parent2*)&child)->grandparent_data = 10;
}
