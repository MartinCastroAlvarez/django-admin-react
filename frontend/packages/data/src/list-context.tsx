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
  /** "Show all N" flag (Django `ALL_VAR`, #385): drop pagination and
   *  fetch every row when `total <= list_max_show_all`. */
  all?: boolean;
  /** `list_filter` query params keyed by descriptor name. */
  filters?: Record<string, string>;
}

export type ListState = SwrState<ListResponse>;

function serializeFilters(filters?: Record<string, string>): string {
  if (!filters) return '';
  return Object.keys(filters)
    .filter((k) => filters[k] !== '' && filters[k] != null)
    .sort()
    .map((k) => `${k}=${filters[k]}`)
    .join('&');
}

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
    p.all ? 'all' : '',
    serializeFilters(p.filters),
  ].join('|');
}

export function useList(params: UseListParams): ListState {
  const cacheKey = cacheKeyFor(params);
  const filtersKey = serializeFilters(params.filters);
  const fetcher = useMemo(
    () => () => {
      const query: Parameters<ApiClient['list']>[2] = {};
      if (params.q !== undefined) query.q = params.q;
      if (params.page !== undefined) query.page = params.page;
      if (params.pageSize !== undefined) query.page_size = params.pageSize;
      if (params.ordering !== undefined) query.ordering = params.ordering;
      if (params.all !== undefined) query.all = params.all;
      if (params.filters !== undefined) query.filters = params.filters;
      return params.client.list(params.appLabel, params.modelName, query);
    },
    // `params.filters` tracked via its serialised form (`filtersKey`)
    // so a new object identity with identical contents doesn't refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      params.client,
      params.appLabel,
      params.modelName,
      params.q,
      params.page,
      params.pageSize,
      params.ordering,
      params.all,
      filtersKey,
    ],
  );
  return useSwrCache<ListResponse>({
    cacheKey,
    fetcher,
    deps: [cacheKey],
    // Keep the list live without a manual reload: poll in the
    // background and re-validate on focus (the hook's default).
    refetchInterval: LIST_REFETCH_INTERVAL_MS,
    // On a filter / page / search change the cache key changes; keep the
    // prior response on screen so the page chrome (columns, header) stays
    // put and only the table shows a loading skeleton, instead of the
    // whole page blanking to a full-page skeleton (#368).
    keepPreviousData: true,
  });
}

// 15s background poll — a sensible "live enough" cadence for an admin
// list without hammering the backend. Focus re-validation (the hook
// default) covers the come-back-to-the-tab case between polls.
const LIST_REFETCH_INTERVAL_MS = 15_000;
