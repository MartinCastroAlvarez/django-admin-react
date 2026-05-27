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
  /**
   * The related model's `(real_app_label, model_name)` — present only
   * when that model is registered on the admin site (#184). When set,
   * the SPA renders the cell as a navigable link to
   * `<mount>/<app_label>/<model_name>/<id>`; when absent (unregistered
   * related model) the cell is plain text, never a link the detail
   * endpoint would 404 on.
   */
  to?: { app_label: string; model_name: string };
}

/**
 * A value the backend marked as safe HTML — produced when a
 * `ModelAdmin` `list_display` / readonly display method returns a
 * Django `SafeString` (`format_html` / `mark_safe`). The SPA renders
 * `html` as markup (Django changelist parity). A plain string is
 * NEVER this shape, so untrusted text stays escaped. See
 * api-contract §4 + SECURITY.md.
 */
export interface HtmlValue {
  html: string;
}

/**
 * A `FileField` / `ImageField` value — the stored file's name, a URL
 * resolved by the consumer's storage backend (`null` when unavailable),
 * and a best-effort byte size (`null` when the backend doesn't expose it
 * cheaply). The SPA renders it as a download link, not raw text.
 */
export interface FileValue {
  name: string;
  url: string | null;
  size: number | null;
}

export type FieldValue =
  | string
  | number
  | boolean
  | null
  | ForeignKeyValue
  | ForeignKeyValue[]
  | HtmlValue
  | FileValue;

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

/** Result of running a bulk action (contract §5.4). */
export interface ActionRunResponse {
  executed: boolean;
  action: string;
  pks?: Array<string | number>;
  /** Present when the action callable returned an HttpResponse. */
  redirect?: string;
}

/** One cascading model in a delete preview: `{model, count}`. */
export interface DeleteCascadeEntry {
  /** `verbose_name_plural` of the cascading model. */
  model: string;
  count: number;
}

/**
 * Cascade preview for a delete (contract §5.3). Mirrors Django admin's
 * delete confirmation: what else gets removed (`cascade`), what's
 * PROTECT-blocked (`protected`), and which extra delete perms are
 * missing (`perms_needed`). `can_delete` is false when anything is
 * protected or a perm is missing.
 */
export interface DeletePreviewResponse {
  object: { pk: string | number; label: string };
  cascade: DeleteCascadeEntry[];
  protected: string[];
  perms_needed: string[];
  can_delete: boolean;
}

/** One drill-down bucket at the current `date_hierarchy` level. */
export interface DateHierarchyBucket {
  /** Year (e.g. 2026), month (1-12), or day-of-month (1-31). */
  value: number;
  count: number;
}

/**
 * `date_hierarchy` drill-down state (api-contract §3.1). Present only
 * when the admin declares `date_hierarchy`. The SPA reads `active` for
 * the current path and `buckets` for the next-level options; clicking a
 * bucket sets `?year=`/`?month=`/`?day=` (hierarchical).
 */
export interface DateHierarchy {
  field: string;
  granularity_options: Array<'year' | 'month' | 'day'>;
  active: { year: number | null; month: number | null; day: number | null };
  buckets: DateHierarchyBucket[];
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
  /** Present only when the admin declares `date_hierarchy`. */
  date_hierarchy?: DateHierarchy;
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

/** One field's header metadata inside an inline.
 *
 * `type` + `required` (added for #54 inline editing) reuse the same
 * closed vocabulary as the top-level `FieldDescriptor`, so the SPA can
 * route an inline field through the same `FieldInput` widget in edit
 * mode. Both are optional for backward-compat with the read-only
 * detail rendering shipped before the enrichment.
 */
export interface InlineFieldMeta {
  name: string;
  label: string;
  readonly: boolean;
  type?: FieldType;
  required?: boolean;
}

/** One existing child row of an inline. */
export interface InlineRow {
  pk: number | string;
  label: string;
  fields: Record<string, FieldValue>;
}

/**
 * One `InlineModelAdmin` surfaced on the detail response (Issue #54).
 * `kind` drives the SPA layout: `tabular` → table rows, `stacked` →
 * card stack. Permissions gate the edit affordances per-inline.
 */
export interface InlineDescriptor {
  name: string;
  label: string;
  kind: 'tabular' | 'stacked';
  fk_name: string;
  child: { app_label: string; model_name: string };
  extra: number;
  min_num: number | null;
  max_num: number | null;
  can_view: boolean;
  can_add: boolean;
  can_change: boolean;
  can_delete: boolean;
  fields: InlineFieldMeta[];
  rows: InlineRow[];
}

/**
 * Visibility + behaviour of Django's save-flow buttons for this view
 * (api-contract §; backend `registry.save_options`). The SPA renders
 * only the buttons whose `show_*` flag is true; it never invents a save
 * routing the backend wouldn't allow.
 */
export interface SaveOptions {
  /** Plain "Save". */
  show_save: boolean;
  /** "Save and continue editing". */
  show_save_and_continue: boolean;
  /** "Save and add another". */
  show_save_and_add_another: boolean;
  /** "Save as new" — change view only, and only when `save_as` is true. */
  show_save_as_new: boolean;
  /** Raw `ModelAdmin.save_as`: a "Save as new" POST creates a fresh object. */
  save_as: boolean;
  /** Raw `ModelAdmin.save_as_continue`: after "Save as new", land on the
   *  new object's change view (true) or the changelist (false). */
  save_as_continue: boolean;
}

export interface DetailResponse {
  app_label: string;
  model_name: string;
  pk: number | string;
  label: string;
  permissions: Permissions;
  fieldsets: FieldsetDescriptor[];
  fields: Record<string, FieldDescriptor>;
  /** `ModelAdmin.inlines` descriptors; always present (empty when none). */
  inlines: InlineDescriptor[];
  /** Save-flow button visibility for the change view. Optional for
   *  back-compat with older backends that didn't emit it. */
  save_options?: SaveOptions;
}

/**
 * Response of `GET /api/v1/<app>/<model>/add/` — the create-form schema
 * for a NEW object. Same field/fieldset shape as the detail response
 * (so one FieldInput renders both), minus the per-object bits (pk,
 * label, inlines). Field values carry the model defaults.
 */
export interface AddFormResponse {
  app_label: string;
  model_name: string;
  permissions: Permissions;
  fieldsets: FieldsetDescriptor[];
  fields: Record<string, FieldDescriptor>;
  /** Save-flow button visibility for the add view (Save / Save-and-add-
   *  another / Save-and-continue). Optional for back-compat. */
  save_options?: SaveOptions;
}

/** One typeahead hit from the autocomplete endpoint (contract §3.2). */
export interface AutocompleteResult {
  id: number | string;
  label: string;
}

export interface AutocompleteResponse {
  results: AutocompleteResult[];
  pagination?: { page: number; page_size: number; has_more: boolean };
}

export interface CreateResponse {
  pk: number | string;
  label: string;
  redirect: string;
}

/**
 * Response of `POST /api/v1/login/` (contract §7) — the package's React
 * login endpoint returns the authenticated user block on success. The
 * shape mirrors `RegistryUser` (the same minimal, self-known fields the
 * registry exposes; no email / groups / perms).
 */
export interface LoginResponse {
  user: RegistryUser;
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

/**
 * One row in an inline write payload (#54 / api-contract §5.2.1):
 * `{pk:null}` = add, `{pk:N, fields}` = change, `{pk:N, DELETE:true}`
 * = delete. Matches the Django-formset row states the backend expects.
 */
export interface InlineWriteItem {
  pk: number | string | null;
  fields?: Record<string, WriteValue>;
  DELETE?: boolean;
}

/** `inlines` block of an update body, keyed by the inline `name`. */
export type InlineWritePayload = Record<string, { items: InlineWriteItem[] }>;

/**
 * PATCH body: parent field values plus an optional `inlines` block the
 * backend routes through the inline formsets (api/views/update.py pops
 * `inlines` before validating the parent form).
 */
export type UpdatePayload = {
  [field: string]: WriteValue | InlineWritePayload | undefined;
  inlines?: InlineWritePayload;
};
