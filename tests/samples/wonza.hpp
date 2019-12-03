#include "classes.hpp"

enum class Cpp11Enum
{
  RED = 10,
  BLUE = 20
};

// scoped-enum 
// altitude may be altitude::high or altitude::low
 enum class altitude: char
{
  high='h',
  low='l', // C++11 allows the extra comma
};

struct Wowza
{
  virtual ~Wowza() = default;
  virtual int foo(int i = 0) = 0;
};

struct Badabang : Wowza
{
  int foo(int) override;

  bool operator==(const Badabang& o) const;
};

template <typename T, typename Q>
void bar(T&& t, Q&& q);

