// useList — fetch + cache the paginated list endpoint.
//
// Thin wrapper around @dar/api's list call + the shared SWR cache
// helper. Page packages MUST consume this hook (never @dar/api
// directly — see CLAUDE.md §7).

import { useMemo } from 'react';

import type { ApiClient, ListResponse } from '@dar/api';

import { type SwrState, useSwrCache } from './swr-cache';

export interface UseListParams {
  client: ApiClient;
  appLabel: string;
  modelName: string;
  q?: string;
  page?: number;
  pageSize?: number;
  ordering?: string;
}

export type ListState = SwrState<ListResponse>;

function cacheKeyFor(p: UseListParams): string {
  // Versioned + parameter-discriminated so two queries with different
  // pagination don't trample each other in localStorage.
  return [
    'dar:list:v1',
    p.appLabel,
    p.modelName,
    p.q ?? '',
    p.page ?? 1,
    p.pageSize ?? 0,
    p.ordering ?? '',
  ].join('|');
}

export function useList(params: UseListParams): ListState {
  const cacheKey = cacheKeyFor(params);
  const fetcher = useMemo(
    () => () => {
      const query: Parameters<ApiClient['list']>[2] = {};
      if (params.q !== undefined) query.q = params.q;
      if (params.page !== undefined) query.page = params.page;
      if (params.pageSize !== undefined) query.page_size = params.pageSize;
      if (params.ordering !== undefined) query.ordering = params.ordering;
      return params.client.list(params.appLabel, params.modelName, query);
    },
    [
      params.client,
      params.appLabel,
      params.modelName,
      params.q,
      params.page,
      params.pageSize,
      params.ordering,
    ],
  );
  return useSwrCache<ListResponse>({
    cacheKey,
    fetcher,
    deps: [cacheKey],
  });
}
