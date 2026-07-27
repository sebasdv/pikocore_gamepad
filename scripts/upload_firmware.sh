#!/usr/bin/env bash
set -euo pipefail

firmware_path="${1:-build-gamepi/pikocore.uf2}"
upload_timeout_seconds="${UPLOAD_TIMEOUT_SECONDS:-20}"

if [[ ! -f "$firmware_path" ]]; then
	echo "firmware not found: $firmware_path" >&2
	exit 1
fi

find_boot_mount() {
	local candidate
	for candidate in \
		/Volumes/RP2350 \
		/Volumes/RPI-RP2 \
		"/media/${USER:-}/RP2350" \
		"/media/${USER:-}/RPI-RP2" \
		"/run/media/${USER:-}/RP2350" \
		"/run/media/${USER:-}/RPI-RP2"
	do
		if [[ -d "$candidate" ]]; then
			printf '%s\n' "$candidate"
			return 0
		fi
	done
	return 1
}

find_pikocore_serial() {
	local candidate
	if [[ -n "${PIKO_SERIAL_PORT:-}" ]]; then
		if [[ -e "$PIKO_SERIAL_PORT" ]]; then
			printf '%s\n' "$PIKO_SERIAL_PORT"
			return 0
		fi
		echo "PIKO_SERIAL_PORT does not exist: $PIKO_SERIAL_PORT" >&2
		return 1
	fi

	for candidate in \
		/dev/cu.usbmodem*378123* \
		/dev/serial/by-id/*pikocore* \
		/dev/ttyACM*
	do
		if [[ -e "$candidate" ]]; then
			printf '%s\n' "$candidate"
			return 0
		fi
	done
	return 1
}

load_with_picotool() {
	if command -v picotool >/dev/null 2>&1 && picotool info >/dev/null 2>&1; then
		echo "Uploading $firmware_path with picotool"
		picotool load -x "$firmware_path"
		return 0
	fi
	return 1
}

copy_to_boot_mount() {
	local boot_mount
	boot_mount="$(find_boot_mount)" || return 1
	echo "Uploading $firmware_path to $boot_mount"
	cp "$firmware_path" "$boot_mount/pikocore.uf2"
	sync
	return 0
}

if load_with_picotool || copy_to_boot_mount; then
	exit 0
fi

serial_port="$(find_pikocore_serial || true)"
if [[ -n "$serial_port" ]]; then
	echo "Requesting BOOTSEL mode through $serial_port"
	if [[ "$(uname -s)" == "Darwin" ]]; then
		if ! stty -f "$serial_port" 1200; then
			echo "The serial port disconnected while requesting BOOTSEL; continuing to wait" >&2
		fi
	else
		if ! stty -F "$serial_port" 1200; then
			echo "The serial port disconnected while requesting BOOTSEL; continuing to wait" >&2
		fi
	fi
else
	echo "No running pikocore serial port found; waiting for a BOOTSEL device" >&2
fi

attempts=$((upload_timeout_seconds * 4))
for ((attempt = 0; attempt < attempts; attempt++)); do
	if load_with_picotool || copy_to_boot_mount; then
		exit 0
	fi
	sleep 0.25
done

echo "Timed out waiting for an RP2350/RPI-RP2 BOOTSEL device." >&2
echo "Hold BOOTSEL while connecting the device, or set PIKO_SERIAL_PORT, then retry." >&2
exit 1
