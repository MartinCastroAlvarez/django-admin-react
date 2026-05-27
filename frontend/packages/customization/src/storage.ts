// Low-level localStorage access for UI customization.
//
// Every read/write is try/catch-wrapped: a customization preference is a
// best-effort convenience, never load-bearing, so private mode, quota
// errors, and SSR all degrade to a silent no-op (the value still works
// in-memory for the session).

export function readString(key: string): string | null {
  try {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeString(key: string, value: string): void {
  try {
    if (typeof localStorage === 'undefined') return;
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable / quota — best effort */
  }
}

export function removeKey(key: string): void {
  try {
    if (typeof localStorage === 'undefined') return;
    localStorage.removeItem(key);
  } catch {
    /* best effort */
  }
}

/** Parse a JSON-encoded value, returning `fallback` when absent or corrupt. */
export function readJSON<T>(key: string, fallback: T): T {
  const raw = readString(key);
  if (raw === null) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

/** JSON-encode and store a value (best effort). */
export function writeJSON(key: string, value: unknown): void {
  try {
    writeString(key, JSON.stringify(value));
  } catch {
    /* unserialisable / storage unavailable — best effort */
  }
}
