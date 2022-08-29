struct grA;
struct grB;
struct grG;
typedef struct grG sG, *pG;
typedef struct grA sA;
typedef sA *pA;
typedef struct grB sB, *pB;

struct grA {
  pA next;
  int data;
  missing **t;
};

struct grB {
  pG g;
  struct grA a[3];
};

struct grG {
  int n;
  sA a;
  pB *tb;
};
