// useDetail — fetch + cache a single object via the detail endpoint.
//
// Thin wrapper around @dar/api's detail call + the shared SWR cache
// helper. Page packages MUST consume this hook (never @dar/api
// directly — see CLAUDE.md §7).

import { useMemo } from 'react';

import type { ApiClient, DetailResponse } from '@dar/api';

import { type SwrState, useSwrCache } from './swr-cache';

export interface UseDetailParams {
  client: ApiClient;
  appLabel: string;
  modelName: string;
  pk: string | number;
}

export type DetailState = SwrState<DetailResponse>;

function cacheKeyFor(p: UseDetailParams): string {
  return `dar:detail:v1:${p.appLabel}|${p.modelName}|${p.pk}`;
}

export function useDetail(params: UseDetailParams): DetailState {
  const cacheKey = cacheKeyFor(params);
  const fetcher = useMemo(
    () => () => params.client.detail(params.appLabel, params.modelName, params.pk),
    [params.client, params.appLabel, params.modelName, params.pk],
  );
  return useSwrCache<DetailResponse>({
    cacheKey,
    fetcher,
    deps: [cacheKey],
    // Keep the detail view live without a manual reload: poll in the
    // background and re-validate on focus (the hook's default). The
    // edit form copies values into local state, so a background refresh
    // never disturbs an in-progress edit.
    refetchInterval: DETAIL_REFETCH_INTERVAL_MS,
  });
}

const DETAIL_REFETCH_INTERVAL_MS = 15_000;
