typedef enum
{
    WDGIF_OFF_MODE,
    WDGIF_SLOW_MODE,
    WDGIF_FAST_MODE
}WdgIf_ModeType;

typedef void (*Wdg_TriggerLocationPtrType)(uint16 timeout);

//typedef int Std_ReturnType;

typedef Std_ReturnType (*Wdg_SetModeLocationPtrType)(WdgIf_ModeType Mode);
