export interface PikoSimModule {
  ccall: (name: string, ret: string | null, argTypes: string[], args: unknown[]) => unknown;
  _malloc: (size: number) => number;
  _free: (ptr: number) => void;
  HEAPU8: Uint8Array;
  HEAPU16: Uint16Array;
  HEAPF32: Float32Array;
}

const LCD_SIZE = 240;
const LCD_PIXELS = LCD_SIZE * LCD_SIZE;
const AUDIO_SCRATCH_FRAMES = 4096;

export class PikoSim {
  private constructor(
    private readonly mod: PikoSimModule,
    private readonly audioScratchPtr: number,
  ) {}

  static async create(customBankBytes?: Uint8Array): Promise<PikoSim> {
    const { default: createPikoSimModule } = await import(
      /* @vite-ignore */ `${import.meta.env.BASE_URL}sim/pikocore_sim.js`
    );
    const mod = (await createPikoSimModule()) as PikoSimModule;
    let bankBytes = customBankBytes;
    if (!bankBytes) {
      const bankResponse = await fetch(`${import.meta.env.BASE_URL}sim/amen_pad_bank.pikobank`);
      if (!bankResponse.ok) {
        throw new Error(`Failed to fetch demo bank: HTTP ${bankResponse.status}`);
      }
      bankBytes = new Uint8Array(await bankResponse.arrayBuffer());
    }
    const bankPtr = mod._malloc(bankBytes.length);
    mod.HEAPU8.set(bankBytes, bankPtr);
    const ok = mod.ccall('piko_init', 'number', ['number', 'number'], [bankPtr, bankBytes.length]);
    mod._free(bankPtr);
    if (!ok) {
      throw new Error(
        customBankBytes ? 'Your bank was rejected by the firmware (too large or invalid)' : 'Bundled demo bank was rejected by the firmware',
      );
    }
    const audioScratchPtr = mod._malloc(AUDIO_SCRATCH_FRAMES * 4);
    return new PikoSim(mod, audioScratchPtr);
  }

  step(budgetMs: number): void {
    this.mod.ccall('piko_step', null, ['number'], [budgetMs]);
  }

  getLcdFrame(): Uint16Array {
    this.mod.ccall('piko_snapshot_lcd', null, [], []);
    const ptr = this.mod.ccall('piko_lcd_ptr', 'number', [], []) as number;
    return this.mod.HEAPU16.subarray(ptr / 2, ptr / 2 + LCD_PIXELS);
  }

  setButtons(mask: number): void {
    this.mod.ccall('piko_set_buttons', null, ['number'], [mask]);
  }

  mapXinput(xinputButtons: number): number {
    return this.mod.ccall('piko_map_xinput', 'number', ['number'], [xinputButtons]) as number;
  }

  pullAudio(maxFrames: number): Float32Array {
    const frames = Math.min(maxFrames, AUDIO_SCRATCH_FRAMES);
    const written = this.mod.ccall(
      'piko_pull_audio',
      'number',
      ['number', 'number'],
      [this.audioScratchPtr, frames],
    ) as number;
    return this.mod.HEAPF32.slice(this.audioScratchPtr / 4, this.audioScratchPtr / 4 + written);
  }

  speed(): number {
    return this.mod.ccall('piko_speed', 'number', [], []) as number;
  }
}
