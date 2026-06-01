// useFormSpec — fetch the ModelAdmin-resolved form spec for the change /
// add view (rest-api 1.4.0+, #59).
//
// Thin wrapper around @dar/api's formSpec call + the shared SWR cache.
// Page packages MUST consume this hook (never @dar/api directly — see
// CLAUDE.md §7). The cache key includes the querystring so a request-aware
// `get_form` swap (`?variant=…`) doesn't read a stale cached spec.

import { useMemo } from 'react';

import type { ApiClient, FormSpecPayload } from '@dar/api';

import { type SwrState, useSwrCache } from './swr-cache';

export interface UseFormSpecParams {
  client: ApiClient;
  appLabel: string;
  modelName: string;
  /** Omit (or empty) for the add-view form. */
  pk?: string | number;
  /** Original change-form querystring, forwarded for request-aware get_form. */
  query?: string;
}

export type FormSpecState = SwrState<FormSpecPayload>;

function cacheKeyFor(p: UseFormSpecParams): string {
  return `dar:formspec:v1:${p.appLabel}|${p.modelName}|${p.pk ?? 'add'}|${p.query ?? ''}`;
}

export function useFormSpec(params: UseFormSpecParams): FormSpecState {
  const cacheKey = cacheKeyFor(params);
  const fetcher = useMemo(
    () => () =>
      params.client.formSpec(params.appLabel, params.modelName, params.pk, params.query),
    [params.client, params.appLabel, params.modelName, params.pk, params.query],
  );
  return useSwrCache<FormSpecPayload>({
    cacheKey,
    fetcher,
    deps: [cacheKey],
    // No background poll: the form spec is read once when the edit form
    // mounts. Re-validating mid-edit could swap the field set under the
    // operator. The detail hook keeps the read view live separately.
  });
}
