#define C1 10
#define C2 12

typedef unsigned char xxx;

typedef unsigned char __u8;
typedef __u8 myu8;

typedef unsigned short __u16;
typedef __u16 myu16;

struct xt_string_info {
    myu16 from_offset;
    myu16 to_offset;
    int (*pfunc)(myu8,int);
    char      algo[C1];
    char      pattern[C2];
    __u8  patlen;
    union {
        struct {
            myu8  invert;
        } v0;

        struct {
            myu8  flags;
        } v1;
    } u;

    /* Used internally by the kernel */
    struct ts_config __attribute__((aligned(8))) *config;
};

