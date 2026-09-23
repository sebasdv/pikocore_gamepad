#include <cstdio>
#include <cstring>

#include "test.h"

namespace simtest {
std::vector<Case>& registry() {
  static std::vector<Case> cases;
  return cases;
}
int g_failures = 0;
}  // namespace simtest

// Uso: pikocore_sim_tests [filtro]  -- corre los tests cuyo nombre contiene filtro.
int main(int argc, char** argv) {
  const char* filter = argc > 1 ? argv[1] : nullptr;
  int run = 0;
  for (const simtest::Case& c : simtest::registry()) {
    if (filter != nullptr && std::strstr(c.name, filter) == nullptr) continue;
    const int before = simtest::g_failures;
    c.fn();
    ++run;
    std::printf("%s %s\n", simtest::g_failures == before ? "ok  " : "FAIL", c.name);
  }
  std::printf("%d tests, %d fallas\n", run, simtest::g_failures);
  return simtest::g_failures == 0 ? 0 : 1;
}
