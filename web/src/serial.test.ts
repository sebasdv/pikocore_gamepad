import { describe, expect, it } from 'vitest';
import {
  BANK_HEADER_SIZE,
  BANK_MAX_SAMPLES,
  BANK_VERSION,
  BANK_WAVEFORM_COLUMNS,
} from './bank';
import { isCompatibleFirmware, parseInfo } from './serial';

const baseInfo = 'PIKO1 FW 2.3 F 16777216 R 524288 S 520192 A 524288 C 16240640 U 0 SR 24000 N 0 CLOCK_INPUT CLOCK';

describe('serial metadata parsing', () => {
  it('parses firmware compatibility tokens', () => {
    const info = parseInfo(
      `${baseInfo} PROTO 1 BANK_VERSION ${BANK_VERSION} BANK_HEADER_SIZE ${BANK_HEADER_SIZE} BANK_MAX_SAMPLES ${BANK_MAX_SAMPLES} BANK_WAVEFORM_COLUMNS ${BANK_WAVEFORM_COLUMNS}\nEND\n`,
    );

    expect(info.firmware).toBe('2.3');
    expect(info.protocolVersion).toBe(1);
    expect(info.bankVersion).toBe(BANK_VERSION);
    expect(info.bankHeaderSize).toBe(BANK_HEADER_SIZE);
    expect(info.bankMaxSamples).toBe(BANK_MAX_SAMPLES);
    expect(info.bankWaveformColumns).toBe(BANK_WAVEFORM_COLUMNS);
  });
});

describe('firmware compatibility', () => {
  it('treats missing metadata as incompatible', () => {
    expect(isCompatibleFirmware(parseInfo(baseInfo))).toBe(false);
  });

  it('treats FW 2.2 without compatibility tokens as incompatible', () => {
    expect(isCompatibleFirmware(parseInfo(baseInfo.replace('FW 2.3', 'FW 2.2')))).toBe(false);
  });

  it('accepts matching v3 waveform bank metadata', () => {
    const info = parseInfo(
      `${baseInfo} PROTO 1 BANK_VERSION ${BANK_VERSION} BANK_HEADER_SIZE ${BANK_HEADER_SIZE} BANK_MAX_SAMPLES ${BANK_MAX_SAMPLES} BANK_WAVEFORM_COLUMNS ${BANK_WAVEFORM_COLUMNS}\nEND\n`,
    );

    expect(isCompatibleFirmware(info)).toBe(true);
  });

  it('rejects wrong bank version', () => {
    const info = parseInfo(`${baseInfo} PROTO 1 BANK_VERSION 2 BANK_HEADER_SIZE ${BANK_HEADER_SIZE} BANK_MAX_SAMPLES ${BANK_MAX_SAMPLES} BANK_WAVEFORM_COLUMNS ${BANK_WAVEFORM_COLUMNS}\nEND\n`);

    expect(isCompatibleFirmware(info)).toBe(false);
  });

  it('rejects wrong header size', () => {
    const info = parseInfo(`${baseInfo} PROTO 1 BANK_VERSION ${BANK_VERSION} BANK_HEADER_SIZE 4096 BANK_MAX_SAMPLES ${BANK_MAX_SAMPLES} BANK_WAVEFORM_COLUMNS ${BANK_WAVEFORM_COLUMNS}\nEND\n`);

    expect(isCompatibleFirmware(info)).toBe(false);
  });

  it('rejects insufficient max sample support', () => {
    const info = parseInfo(`${baseInfo} PROTO 1 BANK_VERSION ${BANK_VERSION} BANK_HEADER_SIZE ${BANK_HEADER_SIZE} BANK_MAX_SAMPLES 32 BANK_WAVEFORM_COLUMNS ${BANK_WAVEFORM_COLUMNS}\nEND\n`);

    expect(isCompatibleFirmware(info)).toBe(false);
  });

  it('rejects missing or wrong waveform metadata', () => {
    const missing = parseInfo(
      `${baseInfo} PROTO 1 BANK_VERSION ${BANK_VERSION} BANK_HEADER_SIZE ${BANK_HEADER_SIZE} BANK_MAX_SAMPLES ${BANK_MAX_SAMPLES}\nEND\n`,
    );
    const wrong = parseInfo(
      `${baseInfo} PROTO 1 BANK_VERSION ${BANK_VERSION} BANK_HEADER_SIZE ${BANK_HEADER_SIZE} BANK_MAX_SAMPLES ${BANK_MAX_SAMPLES} BANK_WAVEFORM_COLUMNS 120\nEND\n`,
    );

    expect(isCompatibleFirmware(missing)).toBe(false);
    expect(isCompatibleFirmware(wrong)).toBe(false);
  });
});
