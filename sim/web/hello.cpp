// sim/web/hello.cpp
#include <cstdio>
#include <emscripten/emscripten.h>

extern "C" EMSCRIPTEN_KEEPALIVE int piko_hello(int x) {
  return x + 1;
}

int main() {
  std::printf("pikocore-sim-web toolchain OK\n");
  return 0;
}
