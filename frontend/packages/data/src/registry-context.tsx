// RegistryProvider — the package's "what does the user see?" cache.
//
// Loads the `/api/v1/registry/` payload at boot, hydrates from
// localStorage for instant first paint, and revalidates over the
// network. Pages read it via `useRegistry()` and never call
// `@dar/api` directly (CLAUDE.md §7).

import { createContext, type PropsWithChildren, useContext, useMemo } from 'react';

import type { ApiClient, RegistryResponse } from '@dar/api';

import { type SwrState, useSwrCache } from './swr-cache';

export type RegistryState = SwrState<RegistryResponse>;

const RegistryContext = createContext<RegistryState | null>(null);

export interface RegistryProviderProps {
  client: ApiClient;
}

export function RegistryProvider({ client, children }: PropsWithChildren<RegistryProviderProps>) {
  // Memoize the bound fetcher so the SWR hook re-fetches only when
  // the client reference actually changes.
  const fetcher = useMemo(() => () => client.getRegistry(), [client]);
  const state = useSwrCache<RegistryResponse>({
    cacheKey: 'dar:registry:v1',
    fetcher,
    deps: [client],
  });

  return <RegistryContext.Provider value={state}>{children}</RegistryContext.Provider>;
}

export function useRegistry(): RegistryState {
  const value = useContext(RegistryContext);
  if (value === null) {
    throw new Error('useRegistry() must be used inside <RegistryProvider>');
  }
  return value;
}
