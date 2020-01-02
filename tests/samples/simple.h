struct S {
  char c;
  int  n;
  union {
    unsigned char x[2];
    unsigned short s;
  } u;
  char (*PtrCharArrayOf3[2])[3];
  void (*pfunc)(int, int);
};
