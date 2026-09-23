#pragma once
// Mini framework de unit tests: sin dependencias externas.
#include <cstdio>
#include <vector>

namespace simtest {
struct Case {
  const char* name;
  void (*fn)();
};
std::vector<Case>& registry();
extern int g_failures;
struct Registrar {
  Registrar(const char* name, void (*fn)()) { registry().push_back({name, fn}); }
};
}  // namespace simtest

#define TEST(name)                                         \
  static void name();                                      \
  static simtest::Registrar name##_registrar(#name, name); \
  static void name()

#define CHECK(cond)                                                           \
  do {                                                                        \
    if (!(cond)) {                                                            \
      std::printf("  FALLO %s:%d: %s\n", __FILE__, __LINE__, #cond);          \
      ++simtest::g_failures;                                                  \
    }                                                                         \
  } while (0)

// Solo para enteros (imprime ambos valores como long long).
// El push/pop de C4127 evita el falso positivo de MSVC cuando a y b son
// ambos constexpr (p. ej. comparar un arreglo constexpr contra un literal):
// el compilador pliega la condición en tiempo de compilación y la marca como
// "siempre constante", aunque el macro sea genérico.
#define CHECK_EQ(a, b)                                                         \
  do {                                                                         \
    const long long va_ = static_cast<long long>(a);                           \
    const long long vb_ = static_cast<long long>(b);                           \
    __pragma(warning(push))                                                    \
    __pragma(warning(disable : 4127))                                          \
    if (va_ != vb_) {                                                          \
      std::printf("  FALLO %s:%d: %s == %s (%lld vs %lld)\n", __FILE__,        \
                  __LINE__, #a, #b, va_, vb_);                                 \
      ++simtest::g_failures;                                                   \
    }                                                                          \
    __pragma(warning(pop))                                                     \
  } while (0)
