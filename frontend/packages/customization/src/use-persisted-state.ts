// React hooks for localStorage-backed UI customization. Every consumer
// used to hand-roll the same "read on init (try/catch), write on change
// (try/catch)" dance; these centralize it.

import { useCallback, useState } from 'react';

import { readJSON, writeJSON } from './storage';

/**
 * A piece of UI state mirrored to localStorage under `key`. Reads once on
 * mount (falling back to `defaultValue`), and writes on every change.
 * Storage failures degrade silently — the value still works in-memory.
 *
 * `key` is assumed stable for the component's lifetime (it identifies the
 * preference); a changing key is not re-read.
 */
export function usePersistedState<T>(
  key: string,
  defaultValue: T,
): [T, (next: T | ((prev: T) => T)) => void] {
  const [value, setValue] = useState<T>(() => readJSON<T>(key, defaultValue));
  const set = useCallback(
    (next: T | ((prev: T) => T)) => {
      setValue((prev) => {
        const resolved = typeof next === 'function' ? (next as (p: T) => T)(prev) : next;
        writeJSON(key, resolved);
        return resolved;
      });
    },
    [key],
  );
  return [value, set];
}

/**
 * A persisted `Set<string>` — the "collapsed groups / hidden columns"
 * shape. Serialised to localStorage as an array. The updater takes the
 * previous Set and returns the next one, so callers keep their own rules
 * (e.g. "never hide the last column") while persistence is centralized.
 */
export function usePersistedSet(
  key: string,
): [Set<string>, (next: (prev: Set<string>) => Set<string>) => void] {
  const [value, setValue] = useState<Set<string>>(() => {
    const arr = readJSON<string[] | null>(key, null);
    return arr ? new Set(arr) : new Set();
  });
  const update = useCallback(
    (next: (prev: Set<string>) => Set<string>) => {
      setValue((prev) => {
        const resolved = next(prev);
        writeJSON(key, [...resolved]);
        return resolved;
      });
    },
    [key],
  );
  return [value, update];
}
