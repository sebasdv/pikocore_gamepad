#include "platform/sim_window.h"

#include <windows.h>
#include <shellapi.h>

#include <string>
#include <vector>

#include "core/buttons.h"
#include "core/file_io.h"
#include "core/st7789.h"

namespace sim {

namespace {

constexpr int kW = 820;
constexpr int kH = 600;
constexpr int kLcdX = 170;
constexpr int kLcdY = 30;
constexpr int kLcdPx = St7789::kSize * 2;  // LCD escalado x2

struct Shape {
  Button button;
  RECT rect;
  bool round;
  const wchar_t* label;
};

// D-pad centrado en (85, 270), botones de cara en (730, 270), con 52 px entre centros.
const Shape kShapes[] = {
    {kUp, {63, 196, 107, 240}, false, L"▲"},
    {kDown, {63, 300, 107, 344}, false, L"▼"},
    {kLeft, {11, 248, 55, 292}, false, L"◀"},
    {kRight, {115, 248, 159, 292}, false, L"▶"},
    {kX, {708, 196, 752, 240}, true, L"X"},
    {kY, {656, 248, 700, 292}, true, L"Y"},
    {kA, {760, 248, 804, 292}, true, L"A"},
    {kB, {708, 300, 752, 344}, true, L"B"},
    {kL, {30, 40, 140, 70}, false, L"L"},
    {kR, {680, 40, 790, 70}, false, L"R"},
    {kSelect, {30, 470, 140, 500}, false, L"SELECT"},
    {kStart, {680, 470, 790, 500}, false, L"START"},
};

struct State {
  const WindowHooks* hooks = nullptr;
  std::filesystem::path capture;
  uint32_t exit_after_ms = 0;
  ULONGLONG start_ms = 0;
  HDC mem_dc = nullptr;
  HBITMAP dib = nullptr;
  HGDIOBJ old_bitmap = nullptr;
  uint32_t* dib_px = nullptr;
  HFONT label_font = nullptr;
  HFONT status_font = nullptr;
  uint16_t keyboard = 0;
  std::vector<uint16_t> lcd = std::vector<uint16_t>(St7789::kSize * St7789::kSize);
  std::vector<uint32_t> lcd_rgb = std::vector<uint32_t>(St7789::kSize * St7789::kSize);
};
State g;

BITMAPINFO bitmap_info(int w, int h) {
  BITMAPINFO bmi = {};
  bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bmi.bmiHeader.biWidth = w;
  bmi.bmiHeader.biHeight = -h;  // de arriba hacia abajo
  bmi.bmiHeader.biPlanes = 1;
  bmi.bmiHeader.biBitCount = 32;
  bmi.bmiHeader.biCompression = BI_RGB;
  return bmi;
}

void fill(HDC dc, const RECT& r, COLORREF color) {
  HBRUSH brush = CreateSolidBrush(color);
  FillRect(dc, &r, brush);
  DeleteObject(brush);
}

void draw_shape(HDC dc, const Shape& s, bool pressed) {
  HBRUSH brush = CreateSolidBrush(pressed ? RGB(235, 235, 235) : RGB(78, 78, 86));
  HPEN pen = CreatePen(PS_SOLID, 1, RGB(20, 20, 24));
  HGDIOBJ old_brush = SelectObject(dc, brush);
  HGDIOBJ old_pen = SelectObject(dc, pen);
  if (s.round) {
    Ellipse(dc, s.rect.left, s.rect.top, s.rect.right, s.rect.bottom);
  } else {
    RoundRect(dc, s.rect.left, s.rect.top, s.rect.right, s.rect.bottom, 10, 10);
  }
  SelectObject(dc, old_brush);
  SelectObject(dc, old_pen);
  DeleteObject(brush);
  DeleteObject(pen);
  SetTextColor(dc, pressed ? RGB(20, 20, 20) : RGB(225, 225, 225));
  RECT r = s.rect;
  DrawTextW(dc, s.label, -1, &r, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
}

void draw_lcd(HDC dc) {
  g.hooks->snapshot_lcd(g.lcd.data());
  const uint32_t backlight = g.hooks->backlight();
  for (size_t i = 0; i < g.lcd.size(); ++i) {
    const uint32_t c = rgb565_to_rgb888(g.lcd[i]);
    const uint32_t r = ((c >> 16) & 255u) * backlight / 65535u;
    const uint32_t gr = ((c >> 8) & 255u) * backlight / 65535u;
    const uint32_t b = (c & 255u) * backlight / 65535u;
    g.lcd_rgb[i] = (r << 16) | (gr << 8) | b;
  }
  const BITMAPINFO bmi = bitmap_info(St7789::kSize, St7789::kSize);
  SetStretchBltMode(dc, COLORONCOLOR);
  StretchDIBits(dc, kLcdX, kLcdY, kLcdPx, kLcdPx, 0, 0, St7789::kSize, St7789::kSize,
                g.lcd_rgb.data(), &bmi, DIB_RGB_COLORS, SRCCOPY);
}

void paint(HDC dc) {
  const RECT all = {0, 0, kW, kH};
  fill(dc, all, RGB(24, 24, 27));

  HBRUSH body = CreateSolidBrush(RGB(52, 52, 58));
  HGDIOBJ old_brush = SelectObject(dc, body);
  HGDIOBJ old_pen = SelectObject(dc, GetStockObject(NULL_PEN));
  RoundRect(dc, 10, 10, 810, 540, 40, 40);
  SelectObject(dc, old_brush);
  SelectObject(dc, old_pen);
  DeleteObject(body);

  const RECT bezel = {kLcdX - 6, kLcdY - 6, kLcdX + kLcdPx + 6, kLcdY + kLcdPx + 6};
  fill(dc, bezel, RGB(0, 0, 0));
  draw_lcd(dc);

  SetBkMode(dc, TRANSPARENT);
  HGDIOBJ old_font = SelectObject(dc, g.label_font);
  const uint16_t mask = g.hooks->button_mask();
  for (const Shape& s : kShapes) draw_shape(dc, s, (mask & bit(s.button)) != 0);

  // LED de beat (GP28)
  HBRUSH led = CreateSolidBrush(g.hooks->beat_led() ? RGB(255, 60, 40) : RGB(70, 30, 30));
  old_brush = SelectObject(dc, led);
  old_pen = SelectObject(dc, GetStockObject(NULL_PEN));
  Ellipse(dc, 78, 113, 93, 128);
  SelectObject(dc, old_brush);
  SelectObject(dc, old_pen);
  DeleteObject(led);

  SelectObject(dc, g.status_font);
  SetTextColor(dc, RGB(170, 170, 170));
  RECT status = {16, 548, kW - 16, 592};
  const std::wstring text = g.hooks->status();
  DrawTextW(dc, text.c_str(), -1, &status, DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS);
  SelectObject(dc, old_font);
}

void capture_and_close(HWND hwnd) {
  KillTimer(hwnd, 1);
  if (!g.capture.empty()) {
    paint(g.mem_dc);
    GdiFlush();
    write_bmp(g.capture, kW, kH, [](int x, int y) {
      return g.dib_px[static_cast<size_t>(y) * kW + x] & 0xFFFFFFu;
    });
  }
  DestroyWindow(hwnd);
}

void set_keyboard(uint16_t mask) {
  g.keyboard = mask;
  g.hooks->keyboard_mask(mask);
}

LRESULT CALLBACK wnd_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
  switch (msg) {
    case WM_CREATE: {
      HDC window_dc = GetDC(hwnd);
      g.mem_dc = CreateCompatibleDC(window_dc);
      ReleaseDC(hwnd, window_dc);
      const BITMAPINFO bmi = bitmap_info(kW, kH);
      g.dib = CreateDIBSection(g.mem_dc, &bmi, DIB_RGB_COLORS,
                               reinterpret_cast<void**>(&g.dib_px), nullptr, 0);
      g.old_bitmap = SelectObject(g.mem_dc, g.dib);
      g.label_font = CreateFontW(-15, 0, 0, 0, FW_BOLD, 0, 0, 0, DEFAULT_CHARSET, 0, 0,
                                 CLEARTYPE_QUALITY, 0, L"Segoe UI");
      g.status_font = CreateFontW(-14, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0,
                                  CLEARTYPE_QUALITY, 0, L"Segoe UI");
      DragAcceptFiles(hwnd, TRUE);
      SetTimer(hwnd, 1, 16, nullptr);
      g.start_ms = GetTickCount64();
      return 0;
    }
    case WM_TIMER:
      if (g.exit_after_ms > 0 && GetTickCount64() - g.start_ms >= g.exit_after_ms) {
        capture_and_close(hwnd);
        return 0;
      }
      InvalidateRect(hwnd, nullptr, FALSE);
      return 0;
    case WM_ERASEBKGND:
      return 1;
    case WM_PAINT: {
      PAINTSTRUCT ps;
      HDC dc = BeginPaint(hwnd, &ps);
      paint(g.mem_dc);
      BitBlt(dc, 0, 0, kW, kH, g.mem_dc, 0, 0, SRCCOPY);
      EndPaint(hwnd, &ps);
      return 0;
    }
    case WM_KEYDOWN:
    case WM_KEYUP:
    case WM_SYSKEYDOWN:
    case WM_SYSKEYUP: {
      const int b = button_for_vk(static_cast<unsigned>(wp));
      if (b < 0) break;
      const bool down = msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN;
      const uint16_t bitmask = bit(static_cast<Button>(b));
      set_keyboard(static_cast<uint16_t>(down ? (g.keyboard | bitmask) : (g.keyboard & ~bitmask)));
      return 0;
    }
    case WM_KILLFOCUS:
      set_keyboard(0);
      return 0;
    case WM_DROPFILES: {
      HDROP drop = reinterpret_cast<HDROP>(wp);
      // Largo real del path (sin el terminador): rutas largas no se cortan en MAX_PATH.
      const UINT len = DragQueryFileW(drop, 0, nullptr, 0);
      if (len > 0) {
        std::wstring path(len + 1, L'\0');
        if (DragQueryFileW(drop, 0, path.data(), len + 1) > 0) {
          path.resize(len);
          g.hooks->file_dropped(path);
        }
      }
      DragFinish(drop);
      return 0;
    }
    case WM_DESTROY:
      KillTimer(hwnd, 1);
      PostQuitMessage(0);
      return 0;
    default:
      break;
  }
  return DefWindowProcW(hwnd, msg, wp, lp);
}

}  // namespace

int run_window(const WindowHooks& hooks, const std::filesystem::path& capture,
               uint32_t exit_after_ms) {
  g.hooks = &hooks;
  g.capture = capture;
  g.exit_after_ms = exit_after_ms;

  HINSTANCE instance = GetModuleHandleW(nullptr);
  WNDCLASSW wc = {};
  wc.lpfnWndProc = wnd_proc;
  wc.hInstance = instance;
  wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
  wc.lpszClassName = L"PikocoreSim";
  RegisterClassW(&wc);

  const DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
  RECT r = {0, 0, kW, kH};
  AdjustWindowRect(&r, style, FALSE);
  HWND hwnd = CreateWindowW(L"PikocoreSim", L"pikocore-sim — GamePi13", style, CW_USEDEFAULT,
                            CW_USEDEFAULT, r.right - r.left, r.bottom - r.top, nullptr, nullptr,
                            instance, nullptr);
  if (hwnd == nullptr) return 1;
  ShowWindow(hwnd, SW_SHOW);

  MSG msg;
  while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
    TranslateMessage(&msg);
    DispatchMessageW(&msg);
  }

  SelectObject(g.mem_dc, g.old_bitmap);
  DeleteObject(g.dib);
  DeleteDC(g.mem_dc);
  DeleteObject(g.label_font);
  DeleteObject(g.status_font);
  return 0;
}

}  // namespace sim
