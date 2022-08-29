struct A;
struct B;
struct G;
typedef struct G sG, *pG;
typedef struct A sA;
typedef sA *pA;
typedef struct B sB, *pB;

struct A {
  pA next;
  int data;
  missing **t;
}

struct B {
  pG g;
  struct A a[3];
}

struct G {
  int n;
  sA a;
  pB *tb;
}
