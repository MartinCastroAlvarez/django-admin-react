// Write helpers — page packages call these instead of @dar/api.
//
// PR #6 ships a thin pass-through (no debounce yet). PR #7 will add:
//  - optimistic updates onto the per-object cache;
//  - debounced batching for rapid edits;
//  - cache invalidation on success.

import type { ActionRunResponse, ApiClient, CreatePayload, UpdatePayload } from '@dar/api';

export interface CreateArgs {
  client: ApiClient;
  appLabel: string;
  modelName: string;
  payload: CreatePayload;
}

export interface UpdateArgs {
  client: ApiClient;
  appLabel: string;
  modelName: string;
  pk: string | number;
  payload: UpdatePayload;
}

export interface DeleteArgs {
  client: ApiClient;
  appLabel: string;
  modelName: string;
  pk: string | number;
}

export function createObject(args: CreateArgs) {
  return args.client.create(args.appLabel, args.modelName, args.payload);
}

export function updateObject(args: UpdateArgs) {
  return args.client.update(args.appLabel, args.modelName, args.pk, args.payload);
}

export function deleteObject(args: DeleteArgs) {
  return args.client.delete(args.appLabel, args.modelName, args.pk);
}

export interface RunActionArgs {
  client: ApiClient;
  appLabel: string;
  modelName: string;
  actionName: string;
  pks: Array<string | number>;
  confirmed?: boolean;
}

export function runAction(args: RunActionArgs): Promise<ActionRunResponse> {
  return args.client.runAction(
    args.appLabel,
    args.modelName,
    args.actionName,
    args.pks,
    args.confirmed ?? false,
  );
}
