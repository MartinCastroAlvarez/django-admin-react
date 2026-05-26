// ApiProvider — wires a single ApiClient instance to React tree.
//
// `@dar/data` is the ONLY package allowed to import `@dar/api`.
// Page packages get the client via the `useApiClient()` hook so they
// never see the network layer directly.

import { createContext, type PropsWithChildren, useContext } from 'react';

import { ApiClient } from '@dar/api';

const ApiContext = createContext<ApiClient | null>(null);

export interface ApiProviderProps {
  client: ApiClient;
}

export function ApiProvider({ client, children }: PropsWithChildren<ApiProviderProps>) {
  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>;
}

export function useApiClient(): ApiClient {
  const client = useContext(ApiContext);
  if (client === null) {
    throw new Error('useApiClient() must be used inside <ApiProvider>');
  }
  return client;
}

export { ApiClient } from '@dar/api';
export type { ApiClientConfig } from '@dar/api';
