#include <stdlib.h>
#include <stdio.h>
#include "simple.h"

typedef unsigned size_type;
size_type size;

int Foo(int n, char c, unsigned x, void* cb) {
    int res;

    res = n+x+atoi(&c);
    return res;
}

int main(int argc, char** argv) {
  int j;
  struct S s;

  s.c = 'A';
  s.n = Foo(1,s.c,2,NULL);
  for (j=0; j<sizeof(s.u.x); j++) {
    s.u.x[j] = 'B';
  }
  size = 0xffffffff;
  return s.n + argc + (int)s.u.s + (int)size;
}
