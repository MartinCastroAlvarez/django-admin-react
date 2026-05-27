// useRecentActions — fetch + cache the index "Recent actions" feed.
//
// Thin wrapper around @dar/api's recent-actions call + the shared SWR
// cache helper. Page packages MUST consume this hook (never @dar/api
// directly — see CLAUDE.md §7).

import { useMemo } from 'react';

import type { RecentActionsResponse } from '@dar/api';

import { useApiClient } from './api-context';
import { type SwrState, useSwrCache } from './swr-cache';

export type RecentActionsState = SwrState<RecentActionsResponse>;

// 30s background poll — the panel tracks new actions without a manual
// reload, at a gentler cadence than the changelist (a user's own action
// feed changes less often than a live list).
const RECENT_ACTIONS_REFETCH_INTERVAL_MS = 30_000;

export function useRecentActions(limit?: number): RecentActionsState {
  const client = useApiClient();
  const fetcher = useMemo(() => () => client.getRecentActions(limit), [client, limit]);
  return useSwrCache<RecentActionsResponse>({
    cacheKey: `dar:recent-actions:v1:${limit ?? 'default'}`,
    fetcher,
    deps: [client, limit],
    refetchInterval: RECENT_ACTIONS_REFETCH_INTERVAL_MS,
  });
}
