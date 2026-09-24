import type { BankSample } from './bank';

const DB_NAME = 'pikocore-studio';
const STORE = 'kv';
const KEY = 'samples';

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Storage can be missing or blocked (private windows, cleared site data); the studio bank is a
// convenience, so every failure resolves quietly instead of breaking the loader.
export async function loadStudioSamples(): Promise<BankSample[]> {
  try {
    const db = await openDb();
    return await new Promise<BankSample[]>((resolve) => {
      const request = db.transaction(STORE).objectStore(STORE).get(KEY);
      request.onsuccess = () => {
        const value = request.result as unknown;
        resolve(Array.isArray(value) ? (value as BankSample[]) : []);
      };
      request.onerror = () => resolve([]);
    });
  } catch {
    return [];
  }
}

export async function saveStudioSamples(samples: BankSample[]): Promise<void> {
  try {
    const db = await openDb();
    await new Promise<void>((resolve) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(samples, KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => resolve();
      tx.onabort = () => resolve();
    });
  } catch {
    // ignore
  }
}
