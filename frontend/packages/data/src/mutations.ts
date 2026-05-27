// Write helpers — page packages call these instead of @dar/api.
//
// PR #6 ships a thin pass-through (no debounce yet). PR #7 will add:
//  - optimistic updates onto the per-object cache;
//  - debounced batching for rapid edits;
//  - cache invalidation on success.

import type {
  ApiClient,
  CreatePayload,
  DeletePreviewResponse,
  ObjectActionRunResponse,
  UpdatePayload,
} from '@dar/api';

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

export type DeletePreviewArgs = DeleteArgs;

export interface RunObjectActionArgs {
  client: ApiClient;
  appLabel: string;
  modelName: string;
  pk: string | number;
  /** The object-action name, re-validated server-side against the admin's
   *  permitted `get_change_actions` set. */
  name: string;
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

export function fetchDeletePreview(args: DeletePreviewArgs): Promise<DeletePreviewResponse> {
  return args.client.deletePreview(args.appLabel, args.modelName, args.pk);
}

/** Run one object-level change-page action (#236). */
export function runObjectAction(args: RunObjectActionArgs): Promise<ObjectActionRunResponse> {
  return args.client.runObjectAction(args.appLabel, args.modelName, args.pk, args.name);
}
