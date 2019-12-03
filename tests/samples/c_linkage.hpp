// Linkage stuff
//--------------

extern "C" void f1(void(*pf)()); // declares a function f1 with C linkage,
                             // which returns void and takes a pointer to a C function
                             // which returns void and takes no parameters
extern "C" typedef void FUNC(); // declares FUNC as a C function type that returns void
                                // and takes no parameters
FUNC f2;            // the name f2 has C++ linkage, but its type is C function
extern "C" FUNC f3; // the name f3 has C linkage and its type is C function void()
void (*pf2)(FUNC*); // the name pf2 has C++ linkage, and its type is
                    // "pointer to a C++ function which returns void and takes one
                    // argument of type 'pointer to the C function which returns void
                    // and takes no parameters'"
extern "C" {
    static void f4();  // the name of the function f4 has internal linkage (no language)
                      // but the function's type has C language linkage
}
