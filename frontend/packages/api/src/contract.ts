// TypeScript types for the v1 API wire contract.
//
// Mirrors `docs/api-contract.md`. Keep this file in lockstep with the
// backend; changes here without the matching contract change are a
// review blocker (see CLAUDE.md §2 rule 1).

export type FieldType =
  | 'string'
  | 'text'
  | 'email'
  | 'url'
  | 'slug'
  | 'integer'
  | 'float'
  | 'decimal'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'time'
  | 'uuid'
  | 'choice'
  | 'foreignkey'
  | 'unsupported';

export interface Permissions {
  view: boolean;
  add: boolean;
  change: boolean;
  delete: boolean;
}

export interface RegistryUser {
  id: number;
  username: string;
  is_staff: boolean;
  is_superuser: boolean;
  display_name: string;
}

export interface RegistryModelEntry {
  /**
   * The *display* app label — equals the group label when the
   * consumer's `AdminSite.get_app_list` returns custom groupings.
   * NOT safe for routing; use `real_app_label`.
   */
  app_label: string;
  /**
   * The model's true `_meta.app_label`. This is the only value that
   * round-trips through the list/detail endpoints (`resolve_model`).
   * Always build URLs as `<mount>/api/v1/<real_app_label>/<model_name>/`.
   * Falls back to `app_label` when the consumer uses the default
   * (ungrouped) `get_app_list`.
   */
  real_app_label: string;
  model_name: string;
  object_name: string;
  verbose_name: string;
  verbose_name_plural: string;
  permissions: Permissions;
}

export interface RegistryAppEntry {
  app_label: string;
  verbose_name: string;
  /**
   * True when `app_label` is a consumer-defined `get_app_list`
   * grouping rather than a real Django app label. Display-only.
   */
  is_group?: boolean;
  models: RegistryModelEntry[];
}

export interface RegistryResponse {
  mount: string;
  user: RegistryUser;
  apps: RegistryAppEntry[];
}

export interface ColumnDescriptor {
  name: string;
  label: string;
  sortable: boolean;
}

export interface ForeignKeyValue {
  id: number | string;
  label: string;
}

export type FieldValue = string | number | boolean | null | ForeignKeyValue | ForeignKeyValue[];

export interface ListRow {
  pk: number | string;
  label: string;
  fields: Record<string, FieldValue>;
}

/** One selectable option in a `choice` / `foreignkey` / `custom` filter. */
export interface FilterOption {
  value: string | number | boolean;
  label: string;
}

/**
 * A `list_filter` descriptor (api-contract §3.3). The `name` is the
 * query-string key; the value sent is `?<name>=<value>`.
 */
export interface FilterDescriptor {
  name: string;
  label: string;
  type: 'boolean' | 'choice' | 'foreignkey' | 'date' | 'custom';
  /** Present for `choice` / `foreignkey` (≤25 options). */
  choices?: FilterOption[];
  /** `custom` (SimpleListFilter) carries its options here. */
  lookups?: FilterOption[];
  to?: { app_label: string; model_name: string };
}

/** One bulk action surfaced from `ModelAdmin.actions`. */
export interface ActionDescriptor {
  name: string;
  label: string;
  description: string;
  requires_confirmation?: boolean;
}

export interface ListResponse {
  app_label: string;
  /** Lowercase, no separators — used to build URLs. Do not display. */
  model_name: string;
  /** Model class name as written (e.g. ``PackageModelDisclaimerDisplayed``). */
  object_name: string;
  /** ``Meta.verbose_name`` (singular). Falls back to the auto-derived form. */
  verbose_name: string;
  /** ``Meta.verbose_name_plural``. Use this for list-view titles. */
  verbose_name_plural: string;
  permissions: Permissions;
  columns: ColumnDescriptor[];
  search_fields: string[];
  /** `list_filter` descriptors; always present (empty array when none). */
  filters: FilterDescriptor[];
  /** Bulk actions from `ModelAdmin.actions`; always present. */
  actions: ActionDescriptor[];
  page: number;
  page_size: number;
  total: number;
  results: ListRow[];
}

export interface FieldChoice {
  value: string | number | boolean | null;
  label: string;
}

export interface FieldDescriptor {
  type: FieldType;
  label: string;
  required: boolean;
  readonly: boolean;
  help_text: string;
  value: FieldValue;
  max_length?: number;
  decimal_places?: number;
  choices?: FieldChoice[];
  to?: { app_label: string; model_name: string };
}

export interface FieldsetDescriptor {
  title: string | null;
  fields: string[];
}

export interface DetailResponse {
  app_label: string;
  model_name: string;
  pk: number | string;
  label: string;
  permissions: Permissions;
  fieldsets: FieldsetDescriptor[];
  fields: Record<string, FieldDescriptor>;
}

export interface CreateResponse {
  pk: number | string;
  label: string;
  redirect: string;
}

export interface FieldErrorEnvelope {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string[]>;
  };
}

/**
 * Wire-shape for a single field value on POST / PATCH.
 *
 * Contract §5.1: FK values are sent as the bare related-pk
 * (``number | string``). The backend ALSO accepts the read
 * envelope ``{id, label}`` for ergonomics, but clients should send
 * the bare pk to stay on the documented contract.
 */
export type WriteValue = string | number | boolean | null;

export type CreatePayload = Record<string, WriteValue>;
export type UpdatePayload = Record<string, WriteValue>;
