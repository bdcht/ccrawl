Examples
========


A simple C case
---------------

In a terminal, open file "ccrawl/tests/samples/header.h".
Open another terminal and within your virtualenv do::

  (venv) user@machine:/tmp % ccrawl -l test1.db collect -C ~/ccrawl/tests/samples
  preprocessing files...
    missing include file for 'missingsys.h'
    missing include file for 'h1.h'
    missing include file for 'folder2/x.h'
  done.
  [  9%] /home/bdcht/code/ccrawl/tests/samples/other/sys.h                          [  0]
  [ 18%] /home/bdcht/code/ccrawl/tests/samples/auto.h                               [  7]
         /home/bdcht/code/ccrawl/tests/samples/other/std.h
  [ 27%] /home/bdcht/code/ccrawl/tests/samples/inclusion_err.h                      [  2]
         /home/bdcht/code/ccrawl/tests/samples/bitfield.h
  [ 36%] /home/bdcht/code/ccrawl/tests/samples/header.h                             [ 38]
         /home/bdcht/code/ccrawl/tests/samples/xxx/yyy/somewhere.h
  [ 45%] /home/bdcht/code/ccrawl/tests/samples/other/h2.h                           [  1]
  [ 54%] /home/bdcht/code/ccrawl/tests/samples/xxx/graph.h                          [  9]
  [ 63%] /home/bdcht/code/ccrawl/tests/samples/cxxabi.h                             [c++]
  [ 72%] /home/bdcht/code/ccrawl/tests/samples/00_empty.h                           [  0]
  [ 81%] /home/bdcht/code/ccrawl/tests/samples/01_volatile.h                        [  2]
  [ 90%] /home/bdcht/code/ccrawl/tests/samples/simple.h                             [  2]
  [100%] /home/bdcht/code/ccrawl/tests/samples/stru.h                               [  1]
  ---------------------------------------------------------------------------------------
  saving database...                                                               [  62]

ccrawl has now collected all "\*.h" files in the samples/ directory.

Let us search for all objects with symbol containing "MY"::

  (venv) user@machine:/tmp % ccrawl -l test1.db search "MY"
  found cMacro identifer "MYSTRING"
  found cMacro identifer "MYEXPR"
  found cMacro identifer "MYMACRO"
  found cMacro identifer "MYCONST"

Search for all typedefs currently in the test1.db local database::

  (venv) user@machine:/tmp % ccrawl -l test1.db select -a "cls=cTypedef"
  found cTypedef identifer "Std_ReturnType"
  found cTypedef identifer "_Rxd_In"
  found cTypedef identifer "WdgIf_ModeType"
  found cTypedef identifer "Wdg_TriggerLocationPtrType"
  found cTypedef identifer "Wdg_SetModeLocationPtrType"
  found cTypedef identifer "Ifx_CPU_SMACON_Bits"
  found cTypedef identifer "xxx"
  found cTypedef identifer "__u8"
  found cTypedef identifer "myu8"
  found cTypedef identifer "__u16"
  found cTypedef identifer "myu16"
  found cTypedef identifer "myinteger"
  found cTypedef identifer "foo"
  found cTypedef identifer "fox"
  found cTypedef identifer "foo1"
  found cTypedef identifer "foo2"
  found cTypedef identifer "mystruct"
  found cTypedef identifer "unspelled"
  found cTypedef identifer "p_unspelled"
  found cTypedef identifer "tags"
  found cTypedef identifer "myunion"
  found cTypedef identifer "pac3"
  found cTypedef identifer "u8"
  found cTypedef identifer "bitfield"
  found cTypedef identifer "sG"
  found cTypedef identifer "pG"
  found cTypedef identifer "sA"
  found cTypedef identifer "pA"
  found cTypedef identifer "sB"
  found cTypedef identifer "pB"
  found cTypedef identifer "X"

Search for all functions prototypes that return a myunion type and have a mystruct type as 2d arg::

  (venv) user@machine:/tmp % ccrawl -l test1.db select prototype 0:myunion 2:mystruct
  myunion myFunc(p_unspelled, mystruct);

Search all constants with value 0x10::

  (venv) user@machine:/tmp % ccrawl -l test1.db select constant 0x10
  MYCONST

Print type "foo2" in C language as then as python ctypes::

  (venv) user@machine:/tmp % ccrawl -l test1.db show -r foo2
  typedef void *(*(*foo2[2])(int, void **))[3];

  (venv) user@machine:/tmp % ccrawl -l test1.db show -f ctypes -r foo2
  foo2 = CFUNCTYPE(POINTER(c_void_p*3), c_int, c_void_p)*2


Print type "p_unspelled" (without and then with recurssion) in C::

  (venv) user@machine:/tmp % ccrawl -l test1.db show p_unspelled
  typedef struct ?_4e1bacec *p_unspelled;

  (venv) user@machine:/tmp % ccrawl -l test1.db show -r p_unspelled
  //identifier unk not found
  typedef unsigned char xxx;
  typedef xxx myinteger;
  struct _mystruct;
  typedef int (*foo)(int, char, unsigned int, void *);
  enum X {
    X_0 = 0,
    X_1 = 1,
    X_2 = 2,
    X_3 = 3
  };
  
  struct _bar {
    enum X x;
  };
  
  struct _mystruct {
    myinteger I;
    int tab[12];
    unsigned char p[16];
    short *s;
    struct _mystruct *next;
    foo func;
    struct _bar bar[2];
  };
  
  typedef struct  {
    char *c[4];
    myinteger (*func[2])(int, foo, struct _mystruct *, int, int, int);
    struct _mystruct stab[18];
    int *x;
    unsigned long long y;
    char (*PtrCharArrayOf3[2])[3];
    union  {
      unsigned int A;
      short w[2];
      myinteger *myi;
      unk unused;
    } sAB;
  } *p_unspelled;


Print type "struct _mystruct" (without recurssion) in ctypes format::

  (venv) user@machine:/tmp % ccrawl -l test1.db show -f ctypes 'struct _mystruct'
  struct__mystruct = type('struct__mystruct',(Structure,),{})

  struct__mystruct._fields_ = [("I", myinteger),
                               ("tab", c_int*12),
                               ("p", c_ubyte*16),
                               ("s", POINTER(c_short)),
                               ("next", POINTER(struct__mystruct)),
                               ("func", foo),
                               ("bar", struct__bar*2)]


Select data structures with a type of length 8 at offset 88 (bytes)::

  (venv) user@machine:/tmp % ccrawl -l test1.db select struct "88:+8"
  struct _mystruct


A more realistic case
---------------------

Let's take a FreeRTOS_ firmware in provided demos: CORTEX_M3_MPS2_QEMU_GCC. Compile the demo,
and strip the resulting RTOSDemo.axf firmware. We want to show how we can easily identify kernel
functions by focusing on known OS structures.

If you open the firmware with Ghidra_ you will end up with about 180 anonymous functions.

Let us assume that we don't have the firmware's source code but
still know that it is build for ARM_CM3 platform and that is uses a FreeRTOS kernel.

We can thus collect all definitions from a *FreeRTOS* kernel (v202212.00). Let us start by
running the preprocessing stage on the FreeRTOS kernel C headers ::

  (venv) user@machine:/tmp % unzip FreeRTOSv202212.00.zip; cd FreeRTOSv202212.00/
  (venv) user@machine:/tmp/FreeRTOSv202212.00 % ccrawl collect --recon FreeRTOS/Source/include FreeRTOS/Source/portable/GCC/ARM_CM3/
  preprocessing files...
    missing include file for 'stddef.h'
    missing include file for 'FreeRTOSConfig.h'
    system file '/usr/include/stdint.h' is used
    system file '/usr/include/stdint.h' is used
  done.

For sure, we don't have the FreeRTOSConfig.h file which provides the kernel configuration for the demo.
Also, some files require "stddef.h" and "stdint.h" from the but clearly we shouldn't use the default
*/usr/include* headers and instead provide the ones from *arm-non-eabi* toolchain.

Replace *[...]* with the appropriate path in the command below and collect the sources with::

  (venv) user@machine:/tmp/FreeRTOSv202212.00 % ccrawl -l freertos.db collect \
     FreeRTOS/Source/include \
     FreeRTOS/Source/portable/GCC/ARM_CM3/ \
     --clang "-I[...]lib/gcc/arm-none-eabi/10.3.1/include -I[...]arm-none-eabi/include"
  preprocessing files...
    system file '[...]/arm-none-eabi/10.3.1/include/stdint.h' is used
    missing include file for 'FreeRTOSConfig.h'
    system file '[...]/arm-none-eabi/10.3.1/include/stddef.h' is used
    system file '[...]/arm-none-eabi/10.3.1/include/stdint.h' is used
  done.
  [ 12%] FreeRTOS/Source/include/atomic.h                                           [319]
         [...]/arm-none-eabi/10.3.1/include/stdint.h
  [ 25%] FreeRTOS/Source/include/StackMacros.h                                      [  2]
         FreeRTOS/Source/include/stack_macros.h
  [ 37%] FreeRTOS/Source/include/message_buffer.h                                   [ 21]
         FreeRTOS/Source/include/stream_buffer.h
  [ 50%] FreeRTOS/Source/include/FreeRTOS.h                                         [636]
         [...]/arm-none-eabi/10.3.1/include/stddef.h
         [...]/arm-none-eabi/10.3.1/include/stdint.h
         FreeRTOS/Source/include/projdefs.h
         FreeRTOS/Source/include/portable.h
  [ 62%] FreeRTOS/Source/include/mpu_prototypes.h                                   [  0]
  [ 75%] FreeRTOS/Source/include/event_groups.h                                     [114]
         FreeRTOS/Source/include/timers.h
  [ 87%] FreeRTOS/Source/include/croutine.h                                         [ 37]
         FreeRTOS/Source/include/list.h
  [100%] FreeRTOS/Source/include/semphr.h                                           [135]
         FreeRTOS/Source/include/queue.h
  ---------------------------------------------------------------------------------------
  saving database...                                                                [835]
  

Let us see how many structures have been collected::

  (venv) user@machine:/tmp % ccrawl -l freertos.db select -a cls=cStruct
  found cStruct identifer "struct __fsid_t"
  found cStruct identifer "struct max_align_t"
  found cStruct identifer "struct xLIST_ITEM"
  found cStruct identifer "struct xLIST"
  found cStruct identifer "struct xTIME_OUT"
  found cStruct identifer "struct xMEMORY_REGION"
  found cStruct identifer "struct xTASK_PARAMETERS"
  found cStruct identifer "struct xTASK_STATUS"


Obviously, anything related to "tasks" is of great interrest: Let's have a look at::

  (venv) user@machine:/tmp % ccrawl -l freertos.db show "struct xTASK_STATUS"
  struct xTASK_STATUS {
    TaskHandle_t xHandle;
    const char *pcTaskName;
    UBaseType_t xTaskNumber;
    eTaskState eCurrentState;
    UBaseType_t uxCurrentPriority;
    UBaseType_t uxBasePriority;
    configRUN_TIME_COUNTER_TYPE ulRunTimeCounter;
    StackType_t *pxStackBase;
    configSTACK_DEPTH_TYPE usStackHighWaterMark;
  };

  (venv) user@machine:/tmp % ccrawl -l freertos.db show "TaskHandle_t"
  typedef struct tskTaskControlBlock *TaskHandle_t;

  (venv) user@machine:/tmp % ccrawl -l freertos.db show "struct tskTaskControlBlock"
  identifier 'struct tskTaskControlBlock' not found


Well, that is weird...we are missing one of the major structure of FreeRTOS.
What happened ? Let's go back to the FreeRTOS sources and find out: the structure
is defined in the kernel's *tasks.c* file which has not been collected. Lets collected
*all* kernel sources, not just headers::

  (venv) user@machine:/tmp/FreeRTOSv202212.00 % rm freertos.db
  (venv) user@machine:/tmp/FreeRTOSv202212.00 % ccrawl -l freertos.db collect --all \
     --clang "-I[...]lib/gcc/arm-none-eabi/10.3.1/include -I[...]arm-none-eabi/include" \
     FreeRTOS/Source/include \
     FreeRTOS/Source/portable/GCC/ARM_CM3/ \
     FreeRTOS/Source/*.c
     [...]
  ---------------------------------------------------------------------------------------
  saving database...                                                               [1478]

Now, everything is defined::

  (venv) user@machine:/tmp % ccrawl -l freertos.db show -r "struct xTASK_STATUS"
  typedef unsigned int __uint32_t;
  typedef __uint32_t uint32_t;
  typedef uint32_t StackType_t;
  typedef unsigned int __uint32_t;
  typedef __uint32_t uint32_t;
  typedef uint32_t TickType_t;
  struct xLIST_ITEM;
  struct xLIST_ITEM;
  typedef unsigned long UBaseType_t;
  struct xMINI_LIST_ITEM {
    TickType_t xItemValue;
    struct xLIST_ITEM *pxNext;
    struct xLIST_ITEM *pxPrevious;
  };
  typedef struct xMINI_LIST_ITEM MiniListItem_t;
  
  struct xLIST {
    UBaseType_t uxNumberOfItems;
    ListItem_t *pxIndex;
    MiniListItem_t xListEnd;
  };
  
  struct xLIST_ITEM {
    TickType_t xItemValue;
    struct xLIST_ITEM *pxNext;
    struct xLIST_ITEM *pxPrevious;
    void *pvOwner;
    struct xLIST *pvContainer;
  };
  typedef struct xLIST_ITEM ListItem_t;
  typedef unsigned char __uint8_t;
  typedef __uint8_t uint8_t;
  
  struct tskTaskControlBlock {
    StackType_t *pxTopOfStack;
    ListItem_t xStateListItem;
    ListItem_t xEventListItem;
    UBaseType_t uxPriority;
    StackType_t *pxStack;
    char pcTaskName[16];
    uint32_t ulNotifiedValue[1];
    uint8_t ucNotifyState[1];
  };
  typedef struct tskTaskControlBlock *TaskHandle_t;
  enum eTaskState {
    eRunning = 0,
    eReady = 1,
    eBlocked = 2,
    eSuspended = 3,
    eDeleted = 4,
    eInvalid = 5
  };
  typedef enum eTaskState eTaskState;
  typedef unsigned short __uint16_t;
  typedef __uint16_t uint16_t;
  
  struct xTASK_STATUS {
    TaskHandle_t xHandle;
    const char *pcTaskName;
    UBaseType_t xTaskNumber;
    eTaskState eCurrentState;
    UBaseType_t uxCurrentPriority;
    UBaseType_t uxBasePriority;
    uint32_t ulRunTimeCounter;
    StackType_t *pxStackBase;
    uint16_t usStackHighWaterMark;
  };


Are there any other structures related to tasks ? ::
  (venv) user@machine:/tmp % ccrawl -v -l freertos.db search "struct .*Task" | grep cTypedef
  found cTypedef identifer "TaskFunction_t"
  found cTypedef identifer "StaticTask_t"
  found cTypedef identifer "TaskHandle_t" with matching value
  found cTypedef identifer "TaskHookFunction_t"
  found cTypedef identifer "eTaskState" with matching value
  found cTypedef identifer "TaskParameters_t"
  found cTypedef identifer "TaskStatus_t"
  found cTypedef identifer "tskTCB" with matching value


Obviously, locating usage of any of these structures in the firmware would be a good start.
Let's open the firmware in Ghidra_, start a bridge_ and send these types
into the *DataType Manager*::

  (venv) user@machine:/tmp % ccrawl -v -l freertos.db export "struct xTASK_STATUS"
  config file '.ccrawlrc' loaded
  loading local database freertos.db ...done
  remote database is: mongodb://xxxxxxxxxxxxxxxxxx
  ghidra_bridge connection with data type manager ghidra.program.database.data.ProgramDataTypeManager@...
  importing types in ccrawl category...
  building data type struct_xTASK_STATUS...done.
  (venv) user@machine:/tmp % ccrawl -l freertos.db export "StaticTask_t"
  (venv) user@machine:/tmp %


Now we will start the interactive console::
  (venv) user@machine:/tmp % ccrawl -v -l freertos.db
  config file '.ccrawlrc' loaded
  loading local database freertos.db ...done
  remote database is: mongodb://xxxxxxxxxxxxxxxxxx
                               _ 
    ___ ___ _ __ __ ___      _| |
   / __/ __| '__/ _` \ \ /\ / / |
  | (_| (__| | | (_| |\ V  V /| |
   \___\___|_|  \__,_| \_/\_/ |_| v1.9.0


  In [1]: from ccrawl.ext.ghidra import *
  ghidra_bridge connection with data type manager ghidra.program.database.data.ProgramDataTypeManager@...
  importing types in ccrawl category...
  In [2]: fm = currentProgram.getFunctionManager()
  In [3]: fm.getFunctionCount()
  Out[3]: 180
  In [4]: ctx.invoke(info,pointer=4,identifier="struct xTASK_STATUS")
  identifier: struct xTASK_STATUS
  class     : cStruct
  source    : FreeRTOS/Source/include/task.h
  tag       : 1673023038.7684903
  size      : 36
  offsets   : [(0, 4), (4, 4), (8, 4), (12, 1), (16, 4), (20, 4), (24, 4), (28, 4), (32, 2)]
  [using 32 bits pointer size]

  In [5]: find_functions_with_type([(0, 4), (4, 4), (8, 4), (12, 1), (16, 4), (20, 4), (24, 4), (28, 4), (32, 2)])
  Out|5]:
  [(<_bridged_ghidra.program.database.function.FunctionDB('FUN_00001b64', ...
    ('param_1',
     [(0, 4),
      (4, 4),
      (8, 4),
      (12, 1),
      (16, 4),
      (20, 4),
      (24, 4),
      (28, 4),
      (32, 2)])),
   (<_bridged_ghidra.program.database.function.FunctionDB('FUN_00002408', ...
    ('param_2',
     [(0, 4),
      (4, 4),
      (8, 4),
      (12, 1),
      (16, 4),
      (20, 4),
      (24, 4),
      (28, 4),
      (32, 2)])),
   (<_bridged_ghidra.program.database.function.FunctionDB('FUN_00002cf4', ...
    ('param_2', [(0, 4), (4, 4), (8, 4), (16, 4)]))]


The script found 3 functions that seem to have parameter of type ``TaskStatus_t*``.
The first two are likely to be indeed good matches since *all* fields are matching...

What functions could that be ? Let's search for functions that have matching prototypes::

  In [5]: for f in db.search(where("cls") == "cFunc"):
     ...:     if "TaskStatus_t" in f["val"]["prototype"]:
     ...:         print(f)
  {'id': 'vTaskGetInfo',
   'val': {'prototype': 'void (TaskHandle_t, TaskStatus_t *, BaseType_t, '
                        'eTaskState)',
           'params': ['xTask', 'pxTaskStatus', 'xGetFreeStackSpace', 'eState'],
           'locs': [],
           'calls': []},
   'cls': 'cFunc',
   'src': 'FreeRTOS/Source/include/task.h',
   'tag': '1673023038.7684903'}
  {'id': 'uxTaskGetSystemState',
   'val': {'prototype': 'UBaseType_t (TaskStatus_t *const, const UBaseType_t, '
                        'uint32_t *const)',
           'params': ['pxTaskStatusArray', 'uxArraySize', 'pulTotalRunTime'],
           'locs': [],
           'calls': []},
   'cls': 'cFunc',
   'src': 'FreeRTOS/Source/include/task.h',
   'tag': '1673023038.7684903'}


And it happens that 'FUN_00002408' unstripped name is indeed 'vTaskGetInfo'.
If we have a look at function 'uxTaskGetSystemState' we can see that its first argument is
an array of tasks status, so 'FUN_00001b64' is more likely another function which apparently
has not been collected. The code of 'uxTaskGetSystemState' from the FreeRTOS kernel, shows
that this function calls 'prvListTasksWithinSingleList' and it happens that this is 'FUN_00001b64'.


Et voilà.

.. _FreeRTOS: https://www.freertos.org
.. _Ghidra: https://ghidra-sre.org/
.. _bridge: https://github.com/justfoxing/ghidra_bridge
