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

/**
 * Run one detail-page action on a single object.
 *
 * Reuses the existing changelist actions runner (#603 revised, v1.4.8):
 * `data.object_actions` on the detail response is now sourced from the
 * standard `ModelAdmin.actions` — same descriptor builder as the list
 * response — so the SPA reuses the same `POST <app>/<model>/actions/
 * <name>/` runner with `pks=[<this pk>]`. No dedicated per-object
 * endpoint, no `django-object-actions` integration.
 *
 * Translates the changelist response shape (`{executed, messages,
 * redirect?}`) into the legacy `{ok, message?, redirect?}` callers
 * already consume — same external contract, simpler wiring.
 */
export async function runObjectAction(
  args: RunObjectActionArgs,
): Promise<ObjectActionRunResponse> {
  const res = await args.client.runAction(args.appLabel, args.modelName, args.name, [args.pk]);
  // First `message_user` message becomes the legacy `message` field —
  // the SPA toasts it on success. Additional messages stay reachable
  // via the full ActionRunResponse if a caller wants to upgrade off
  // the legacy shape.
  const message = res.messages && res.messages.length > 0 ? res.messages[0]?.message : undefined;
  return {
    ok: res.executed,
    ...(message !== undefined ? { message } : {}),
    ...(res.redirect !== undefined ? { redirect: res.redirect } : {}),
  };
}
