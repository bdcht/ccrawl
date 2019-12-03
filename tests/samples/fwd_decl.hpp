class Vector; // forward declaration
class Matrix {
    // ...
    friend Vector operator*(const Matrix&, const Vector&);
};
class Vector {
    // ...
    friend Vector operator*(const Matrix&, const Vector&);
};
