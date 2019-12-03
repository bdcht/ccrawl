// Derived Classes
//----------------

class Base {
 protected:
     int d;
};

class Derived : public Base {
 public:
    using Base::d; // make Base's protected member d a public member of Derived
    using Base::Base; // inherit all parent's constructors (C++11)
};

struct vBase {
   virtual void f() {
       std::cout << "base\n";
   }
};

struct vDerived : private vBase {
   void f() override { // 'override' is optional
       std::cout << "derived\n";
   }
};

