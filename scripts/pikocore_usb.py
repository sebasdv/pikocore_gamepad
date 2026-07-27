#!/usr/bin/env python3
"""Query pikocore diagnostics through its silent USB request/response API."""

from __future__ import annotations

import argparse
import glob
import os
import select
import struct
import sys
import termios
import time
from pathlib import Path


MAX_RESPONSE_BYTES = 4096


def find_device() -> str:
    patterns = (
        "/dev/serial/by-id/*pikocore*",
        "/dev/serial/by-id/*Raspberry_Pi_Pico*",
        "/dev/cu.usbmodem*",
        "/dev/tty.usbmodem*",
        "/dev/ttyACM*",
    )
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    raise RuntimeError("pikocore USB serial device not found")


class PikocoreUsb:
    def __init__(self, device: str, timeout: float) -> None:
        self.device = device
        self.timeout = timeout
        self.fd = -1

    def __enter__(self) -> "PikocoreUsb":
        self.fd = os.open(
            self.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK
        )
        attributes = termios.tcgetattr(self.fd)
        attributes[0] = 0
        attributes[1] = 0
        attributes[2] &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
        attributes[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
        attributes[3] = 0
        attributes[4] = termios.B115200
        attributes[5] = termios.B115200
        attributes[6][termios.VMIN] = 0
        attributes[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW, attributes)
        termios.tcflush(self.fd, termios.TCIOFLUSH)
        return self

    def __exit__(self, *_: object) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def _write_all(self, payload: bytes) -> None:
        sent = 0
        deadline = time.monotonic() + self.timeout
        while sent < len(payload):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("timed out writing USB request")
            _, writable, _ = select.select([], [self.fd], [], remaining)
            if writable:
                sent += os.write(self.fd, payload[sent:])

    def _read_some(self, deadline: float, max_bytes: int = 1024) -> bytes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("timed out waiting for USB response")
        readable, _, _ = select.select([self.fd], [], [], remaining)
        if not readable:
            raise TimeoutError("timed out waiting for USB response")
        return os.read(self.fd, max_bytes)

    def _read_exact(self, size: int) -> bytes:
        response = bytearray()
        deadline = time.monotonic() + self.timeout
        while len(response) < size:
            chunk = self._read_some(deadline, size - len(response))
            if chunk:
                response.extend(chunk)
        if len(response) != size:
            raise RuntimeError("USB response framing error")
        return bytes(response)

    def _read_line(self) -> str:
        response = bytearray()
        deadline = time.monotonic() + self.timeout
        while True:
            chunk = self._read_some(deadline)
            if not chunk:
                continue
            response.extend(chunk)
            newline = response.find(b"\n")
            if newline >= 0:
                return response[:newline].rstrip(b"\r").decode(
                    "ascii", errors="replace"
                )

    def sync(self) -> None:
        termios.tcflush(self.fd, termios.TCIFLUSH)
        self._write_all(b"QX")
        marker = b"SYNC\n"
        response = bytearray()
        deadline = time.monotonic() + self.timeout
        while marker not in response:
            chunk = self._read_some(deadline)
            if chunk:
                response.extend(chunk)
            if len(response) > MAX_RESPONSE_BYTES:
                del response[:-len(marker)]

    def line_request(self, command: bytes, *, sync: bool = True) -> str:
        if sync:
            self.sync()
        self._write_all(command)
        return self._read_line()

    def payload_request(self, command: bytes, *, sync: bool = True) -> str:
        if sync:
            self.sync()
        self._write_all(command)
        length = struct.unpack("<I", self._read_exact(4))[0]
        if length == 0 or length > MAX_RESPONSE_BYTES:
            raise RuntimeError(f"invalid USB response length {length}")
        return self._read_exact(length).decode("ascii", errors="replace").strip()

    def status(self, *, sync: bool = True) -> str:
        return self.payload_request(b"D", sync=sync)


def require_ok(response: str) -> str:
    if not response.startswith("OK"):
        raise RuntimeError(response)
    return response


def parse_status(response: str) -> dict[str, int]:
    require_ok(response)
    result: dict[str, int] = {}
    for field in response.split()[2:]:
        if "=" not in field:
            continue
        name, value = field.split("=", 1)
        result[name] = int(value, 0)
    return result


def profile(serial: PikocoreUsb, duration: float) -> None:
    require_ok(serial.line_request(b"Z"))
    time.sleep(duration)
    status = parse_status(serial.status())
    frames = status.get("frames", 0)
    total_us = status.get("render_total_us", 0)
    average_us = total_us / frames if frames else 0.0
    budget_us = status["budget_us_x1000"] / 1000.0
    cpu_percent = average_us * 100.0 / budget_us
    print(
        "duration_s,frames,average_render_us,cpu_percent,max_render_us,"
        "over_budget,max_interval_us"
    )
    print(
        f"{duration:.3f},{frames},{average_us:.3f},{cpu_percent:.2f},"
        f"{status.get('render_max_us', 0)},"
        f"{status.get('render_over_budget', 0)},"
        f"{status.get('interval_max_us', 0)}"
    )


def watch(serial: PikocoreUsb, interval: float) -> None:
    serial.sync()
    while True:
        print(serial.status(sync=False), flush=True)
        time.sleep(interval)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", help="serial device; defaults to auto-detect")
    parser.add_argument("--timeout", type=float, default=2.0)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("ping", "help", "status", "stats-reset"):
        commands.add_parser(action)
    profile_parser = commands.add_parser("profile")
    profile_parser.add_argument("--duration", type=float, default=1.0)
    watch_parser = commands.add_parser("watch")
    watch_parser.add_argument("--interval", type=float, default=1.0)
    return parser


def main() -> int:
    args = create_parser().parse_args()
    if args.timeout <= 0:
        raise ValueError("timeout must be positive")
    device = args.device or find_device()
    if not Path(device).exists():
        raise RuntimeError(f"serial device does not exist: {device}")

    with PikocoreUsb(device, args.timeout) as serial:
        if args.action == "ping":
            print(require_ok(serial.line_request(b"P")))
        elif args.action == "help":
            print(require_ok(serial.line_request(b"H")))
        elif args.action == "status":
            print(require_ok(serial.status()))
        elif args.action == "stats-reset":
            print(require_ok(serial.line_request(b"Z")))
        elif args.action == "profile":
            if args.duration <= 0:
                raise ValueError("profile duration must be positive")
            profile(serial, args.duration)
        elif args.action == "watch":
            if args.interval < 0.1:
                raise ValueError("watch interval must be at least 0.1 seconds")
            watch(serial, args.interval)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (OSError, RuntimeError, TimeoutError, ValueError) as error:
        print(f"pikocore_usb: {error}", file=sys.stderr)
        raise SystemExit(1)
