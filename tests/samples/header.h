#ifndef TEST_H
#define TEST_H

#include "yyy/somewhere.h"

#define MYCONST 0x10             // MYCONST macro
#define MYEXPR (1<<2)
#define MYMACRO(a) ((a+4))
#define MYSTRING "toto"

typedef xxx myinteger;
typedef int (*foo) (int, int, int);
typedef int (*(*foo1)(void ))[3];  // declare foo1 as ptr to func(void) returning ptr to int[3]
typedef void *(*(*foo2[2])( int, void * [] ))[3];

struct _mystruct;

enum X {
  X_0,
  X_1,
  X_2,
  X_3
};

struct _mystruct {
    myinteger   I;                /* comment for field I */
    signed int   tab[MYMACRO(8)];        // modern comment for tab
    unsigned char p[MYCONST];
    short int *s;
    struct _mystruct* next;
    foo func;
    struct _bar {
        enum X x;
    } bar[2];
};

typedef struct _mystruct mystruct;

struct testconst {
    const unsigned char* ptr;
    unsigned char const* cs1;
    unsigned const char* cs2;
    unsigned char* const constp;
    char const (* const CP1[2])[3];
    char* const (* const CP2[2])[3];
};

/* top-level comment above struct */
typedef struct {
    /* above comment for c */
    char* c[MYEXPR];
    void (*func[2]) (myinteger,foo,struct _mystruct*);  // comment for func
    unsigned struct _mystruct stab[0x12];
    signed *x;
    unsigned long long y;
    char (*PtrCharArrayOf3[2])[3];
    union {
       // above comment for union.A
       unsigned int A;
       short w[2];
       myinteger* myi;
    } sAB;
} unspelled, *p_unspelled;

typedef enum {
  TAG0 = 0,
  TAG1 = 1,
  TAG2 = (1<<1)
} tags;

typedef union _myunion {
  char name[TAG2];
  short id;
} myunion;

myunion myFunc(p_unspelled p, mystruct X);
typedef char (*pac3)[3];

#endif