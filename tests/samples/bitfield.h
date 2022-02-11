/** \brief CPUx SIST Mode Access Control Register */
typedef struct _Ifx_CPU_SMACON_Bits
{
    Ifx_Strict_32Bit reserved_0:24;    /**< \brief [23:0] \internal Reserved */
    Ifx_Strict_32Bit IODT:1;          /**< \brief [24:24] In-Order Data Transactions - IODT (rw) */
    Ifx_Strict_32Bit reserved_25:7;    /**< \brief [31:25] \internal Reserved */
} Ifx_CPU_SMACON_Bits;

