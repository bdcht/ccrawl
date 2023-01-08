typedef unsigned int sometype;

#ifdef CONDITION
typedef unsigned int zzz;
#endif

#if CONDITION == 1
typedef unsigned char xMPU_SETTINGS;
#endif

typedef struct Variable
{
    volatile sometype* ptr;
    zzz X;
    #if ( CONDITION == 1 )
        xMPU_SETTINGS xMPUSettings;
    #endif
} V;

