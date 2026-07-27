import { describe, expect, it } from 'vitest';
import {
  BANK_HEADER_SIZE,
  BANK_MAGIC,
  BANK_MAX_SAMPLES,
  BANK_SAMPLE_RATE,
  BANK_SAMPLE_RECORD_SIZE,
  BANK_VERSION,
  BANK_WAVEFORM_BYTES,
  BANK_WAVEFORM_COLUMNS,
  buildBankBlob,
  generateWaveformPeaks,
  parseBankBlob,
  type BankSample,
} from './bank';
import { estimateBpmFromFrames, inferBeatsFromName, inferBpmFromName } from './audio';

function sample(index: number, pcm = new Uint8Array([index & 0xff])): BankSample {
  return {
    id: String(index),
    name: `Sample ${index + 1}`,
    bpm: 170,
    beats: 8,
    peak: 64,
    pcm,
    cropStart: 0,
    cropEnd: pcm.length,
  };
}

describe('pikocore bank format', () => {
  it('round-trips sample metadata and raw pcm', () => {
    const pcm = new Uint8Array([0, 1, 255, 128]);
    const blob = buildBankBlob(
      [
        {
          id: 'a',
          name: 'Amen',
          bpm: 170,
          beats: 16,
          peak: 127,
          pcm,
          cropStart: 1,
          cropEnd: 3,
        },
      ],
      1024,
    );

    const parsed = parseBankBlob(blob);
    expect(parsed.samples).toHaveLength(1);
    expect(parsed.samples[0].name).toBe('Amen');
    expect(parsed.samples[0].bpm).toBe(170);
    expect(parsed.samples[0].beats).toBe(16);
    expect(Array.from(parsed.samples[0].pcm)).toEqual([1, 255]);
  });

  it('generates a complete 240-column min/max waveform', () => {
    const pcm = Uint8Array.from({ length: BANK_WAVEFORM_COLUMNS * 2 }, (_, index) => (index % 2 === 0 ? 0 : 255));
    const waveform = generateWaveformPeaks(pcm);

    expect(waveform).toHaveLength(BANK_WAVEFORM_BYTES);
    expect(Array.from(waveform.slice(0, BANK_WAVEFORM_COLUMNS))).toEqual(
      Array(BANK_WAVEFORM_COLUMNS).fill(0),
    );
    expect(Array.from(waveform.slice(BANK_WAVEFORM_COLUMNS))).toEqual(
      Array(BANK_WAVEFORM_COLUMNS).fill(255),
    );
  });

  it('stores each precomputed waveform immediately before its pcm', () => {
    const pcm = Uint8Array.from({ length: BANK_WAVEFORM_COLUMNS * 2 }, (_, index) => (index % 2 === 0 ? 32 : 224));
    const blob = buildBankBlob([sample(0, pcm)], BANK_WAVEFORM_BYTES + pcm.length);
    const view = new DataView(blob.buffer);
    const pcmOffset = view.getUint32(32, true);

    expect(pcmOffset).toBe(BANK_WAVEFORM_BYTES);
    expect(Array.from(blob.slice(BANK_HEADER_SIZE, BANK_HEADER_SIZE + BANK_WAVEFORM_COLUMNS))).toEqual(
      Array(BANK_WAVEFORM_COLUMNS).fill(32),
    );
    expect(
      Array.from(
        blob.slice(
          BANK_HEADER_SIZE + BANK_WAVEFORM_COLUMNS,
          BANK_HEADER_SIZE + BANK_WAVEFORM_BYTES,
        ),
      ),
    ).toEqual(Array(BANK_WAVEFORM_COLUMNS).fill(224));
    expect(Array.from(blob.slice(BANK_HEADER_SIZE + pcmOffset))).toEqual(Array.from(pcm));
  });

  it('builds and parses a full 128-sample bank', () => {
    const samples = Array.from({ length: BANK_MAX_SAMPLES }, (_, index) => sample(index));
    const payloadBytes = samples.length * (BANK_WAVEFORM_BYTES + 1);
    const blob = buildBankBlob(samples, payloadBytes);
    const parsed = parseBankBlob(blob);

    expect(blob).toHaveLength(BANK_HEADER_SIZE + payloadBytes);
    expect(parsed.samples).toHaveLength(BANK_MAX_SAMPLES);
    expect(parsed.samples[127].name).toBe('Sample 128');
    expect(Array.from(parsed.samples[127].pcm)).toEqual([127]);
  });

  it('rejects more than 128 samples', () => {
    const samples = Array.from({ length: BANK_MAX_SAMPLES + 1 }, (_, index) => sample(index));

    expect(() => buildBankBlob(samples, samples.length)).toThrow('pikocore supports up to 128 samples');
  });

  it('rejects v2 banks without precomputed waveforms as unsupported', () => {
    const blob = new Uint8Array(BANK_HEADER_SIZE);
    const view = new DataView(blob.buffer);
    view.setUint32(0, BANK_MAGIC, true);
    view.setUint32(4, 2, true);
    view.setUint32(8, BANK_HEADER_SIZE, true);

    expect(() => parseBankBlob(blob)).toThrow('Unsupported pikocore bank');
  });

  it('rejects a v3 sample record without its waveform prefix', () => {
    const blob = new Uint8Array(BANK_HEADER_SIZE + 1);
    const view = new DataView(blob.buffer);
    view.setUint32(0, BANK_MAGIC, true);
    view.setUint32(4, BANK_VERSION, true);
    view.setUint32(8, BANK_HEADER_SIZE, true);
    view.setUint32(12, BANK_SAMPLE_RATE, true);
    view.setUint32(16, 1, true);
    view.setUint32(20, 1, true);
    view.setUint32(32, 0, true);
    view.setUint32(36, 1, true);
    view.setUint16(40, 170, true);
    view.setUint16(42, 8, true);

    expect(() => parseBankBlob(blob)).toThrow('Sample waveform is missing');
  });

  it('rejects banks that exceed audio capacity', () => {
    expect(() => buildBankBlob([sample(0, new Uint8Array([1, 2]))], BANK_WAVEFORM_BYTES + 1)).toThrow(
      'Audio bank exceeds device capacity',
    );
  });

  it('keeps all sample records inside the v3 header', () => {
    expect(32 + BANK_MAX_SAMPLES * BANK_SAMPLE_RECORD_SIZE).toBeLessThanOrEqual(BANK_HEADER_SIZE);
  });
});

describe('BPM detection', () => {
  it('prefers filename bpm', () => {
    expect(inferBpmFromName('break_bpm170.wav')).toBe(170);
  });

  it('prefers filename beats', () => {
    expect(inferBeatsFromName('amen_beats16_bpm170.wav')).toBe(16);
  });

  it('estimates loop bpm from duration', () => {
    expect(estimateBpmFromFrames(526629)).toBe(175);
  });
});
