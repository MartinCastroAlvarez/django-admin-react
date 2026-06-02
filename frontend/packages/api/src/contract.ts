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
  // Structured types the backend emits (#242). `json` / `duration` /
  // `array` / `range` have editable SPA widgets. `range` values arrive as
  // the documented envelope `{subtype, value: {lower, upper, bounds}}`
  // (see `docs/api-contract.md` §range types) and write back as a
  // `[lower, upper]` pair (#533).
  | 'json'
  | 'duration'
  | 'array'
  | 'range'
  | 'choice'
  | 'foreignkey'
  | 'manytomany'
  | 'unsupported';

/**
 * Presentational widget hint that overrides the default control the SPA
 * would pick from `type`. `radio` / `raw_id` come from `radio_fields` /
 * `raw_id_fields` (#251). `password` is a security boundary, not a layout
 * choice: it marks a field the admin routed through `PasswordInput`, whose
 * stored value the backend redacts from the payload (matching Django's
 * `render_value=False`) — the SPA masks the input (#504). `shuttle_h` /
 * `shuttle_v` come from `filter_horizontal` / `filter_vertical` (#627) —
 * the SPA renders Django's two-pane "available / chosen" widget for the
 * M2M field, with horizontal or vertical orientation respectively.
 * `custom` (api 1.3.0+) marks a field whose bound form widget class lives
 * outside `django.*` — `formfield_overrides` / `formfield_for_dbfield` /
 * a third-party widget. The SPA dispatches to a consumer-registered
 * widget via `registerFieldWidget(widget_class, …)` (#625); falls back
 * to the default control + an "open in legacy admin" note when no
 * registration matches.
 *
 * The remaining hints map the form-spec `widget.kind` values that need a
 * different control than `FieldType` alone implies (#664):
 * `hidden` (render a real hidden input, never a visible field);
 * `split_datetime` (`SplitDateTimeWidget` — two controls: date + time);
 * `select_date` (`SelectDateWidget` — month / day / year selects);
 * `checkbox_multiple` (a checkbox bank) / `select_multiple` (a native
 * `<select multiple>`) for non-relational multi-value choice fields;
 * `autocomplete` / `autocomplete_multiple` (`autocomplete_fields` typeahead);
 * `file` (a file input — upload itself is tracked under #241, so this is a
 * deliberately limited control with an operator note);
 * `unsupported_widget` is the explicit tracked-fallback for any kind with
 * no faithful control yet — it renders the default control plus a visible
 * operator note (mirroring the `custom`-unregistered branch) so a gap is
 * never a silent wrong control.
 */
export type WidgetHint =
  | 'radio'
  | 'raw_id'
  | 'password'
  | 'shuttle_h'
  | 'shuttle_v'
  | 'custom'
  | 'hidden'
  | 'split_datetime'
  | 'select_date'
  | 'checkbox_multiple'
  | 'select_multiple'
  | 'autocomplete'
  | 'autocomplete_multiple'
  | 'file'
  | 'unsupported_widget';

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

/**
 * A consumer's bespoke admin page reached via `ModelAdmin.get_urls()`
 * (Issue #439). The SPA links out to it — a real `<a target="_blank">`
 * to the Django-rendered page — since it can't render the page itself.
 *
 * - `level: 'object'` — a per-object tool view; `url` already carries
 *   the object's pk (only present on the detail response).
 * - `level: 'changelist'` — a model-wide page (report / import); `url`
 *   takes no object (can appear on the registry model entry too).
 */
export interface CustomView {
  /** The URL pattern name (a stable id for the route). */
  name: string;
  /** Humanized name, or the view callable's `short_description`. */
  label: string;
  /** The reversed admin URL (object-level URLs carry the pk). */
  url: string;
  level: 'object' | 'changelist';
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
  /**
   * Changelist-level custom admin views for this model (Issue #439).
   * Object-level views live on the detail response, not here. Optional;
   * absent when the model's admin exposes no custom routes.
   */
  custom_views?: CustomView[];
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

/** The kind of admin action a `LogEntry` records (`GET recent-actions/`). */
export type RecentActionKind = 'added' | 'changed' | 'deleted' | 'unknown';

/** One entry in the index "Recent actions" feed (#502). `target` is the
 *  affected object's change-page locator, or `null` when it can't be
 *  linked (a deletion, an unregistered model, or no view permission). */
export interface RecentAction {
  id: number;
  action: RecentActionKind;
  /** ISO-8601 timestamp of the action. */
  action_time: string;
  /** The object's string representation at the time of the action. */
  object_repr: string;
  target: { app_label: string; model_name: string; pk: string } | null;
}

/** `GET /api/v1/recent-actions/` — the signed-in user's own recent
 *  actions, newest first. */
export interface RecentActionsResponse {
  actions: RecentAction[];
}

export interface ColumnDescriptor {
  name: string;
  label: string;
  sortable: boolean;
  /** True when the column is in `ModelAdmin.list_editable` — the SPA
   *  renders an inline-editable cell and submits via the bulk endpoint. */
  editable?: boolean;
  /** The column's field type, present only when the column maps to a
   *  concrete model field (absent for `list_display` callables / display
   *  methods). Drives display formatting — e.g. `datetime`/`date`/`time`
   *  cells render localized instead of raw ISO (#413). */
  type?: FieldType;
}

/** One row in a bulk PATCH (`{pk, fields}`) — `PATCH <app>/<model>/bulk/`. */
export interface BulkUpdateEntry {
  pk: string | number;
  fields: Record<string, WriteValue>;
}

/** Bulk PATCH result envelope (#61 / list_editable #243). */
export interface BulkUpdateResponse {
  results: Array<{
    pk: string | number | null;
    ok: boolean;
    error?: { code?: string; message?: string; fields?: Record<string, string[]> };
    rolled_back?: boolean;
  }>;
  summary: { accepted: number; rejected: number };
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
  /**
   * The lookup a `custom` (SimpleListFilter) filter is currently
   * applying — `filter.value()`. Includes a default the filter applies
   * when no querystring param is present, so the SPA reflects it as
   * selected instead of "All" (#283). `null` / absent means no selection.
   */
  selected?: string | null;
}

/**
 * One action surfaced from `ModelAdmin.actions`. The API classifies
 * each registered callable by signature (api 1.0.6+, #603 revised):
 *
 * - `batch` — third parameter is the changelist queryset
 *   (stock Django `def my_action(self, request, queryset)`). Renders
 *   on the **changelist** with multi-select.
 * - `detail` — third parameter is a single object id (parameter
 *   named `obj_id` / `pk` / etc., or annotated `str` / `int` /
 *   `Model`). Renders on the **single-object detail page**.
 *
 * Older API versions (<1.0.6) omit the `target` field; callers
 * should default to `'batch'` for back-compat.
 */
export interface ActionDescriptor {
  name: string;
  label: string;
  description: string;
  requires_confirmation?: boolean;
  /** Render surface for this action (api 1.0.6+). Absent on older
   *  servers; treat as `'batch'` (the legacy/stock Django shape). */
  target?: 'batch' | 'detail';
}

/** Result of running a bulk action (contract §5.4). */
/** A `ModelAdmin.message_user` message surfaced from a run (#442). */
export interface UserMessage {
  /** Django's level tag: `success` / `info` / `warning` / `error` / `debug`. */
  level: string;
  message: string;
}

export interface ActionRunResponse {
  executed: boolean;
  action: string;
  pks?: Array<string | number>;
  /** Present when the action callable returned an HttpResponse. */
  redirect?: string;
  /** Messages the action queued via `message_user` — the SPA toasts them (#442). */
  messages?: UserMessage[];
}

/**
 * One detail-page action descriptor. As of api 1.0.6+ (#603 revised),
 * `data.object_actions` on the detail response uses the same
 * descriptor shape as `data.actions` on the list response — the API
 * builds both from `actions_payload(...)` and classifies each by
 * signature (`target: 'batch' | 'detail'`). `ObjectActionDescriptor`
 * is kept as an alias for backwards-compat with the v1.0.2 → v1.4.7
 * `<ObjectActionButton>` consumer that still imports the name.
 */
export type ObjectActionDescriptor = ActionDescriptor;

/**
 * Result of running one object action
 * (`POST <app>/<model>/<pk>/action/<name>/`, #236). `ok` is false when the
 * action callable raised (the API returns 400, never a 500). `redirect`
 * carries the target URL when the callable returned a redirect response —
 * the SPA navigates client-side rather than following a 302.
 */
export interface ObjectActionRunResponse {
  ok: boolean;
  /** Convenience: first `messages[]` entry's text — kept for back-compat
   *  with v1.4.x consumers that only ever toasted one line. */
  message?: string;
  /** Every `message_user` line with its Django level tag (#632 — needed
   *  so the SPA can pick red / amber / blue / green per level instead of
   *  always toasting green on the detail page). */
  messages?: UserMessage[];
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
  /**
   * Name of the model's primary-key field (usually `id`). When this
   * field appears in `columns`, the SPA pins that column first, never
   * truncates it, and keeps it from being hidden — the pk is the row's
   * identity and must stay fully readable.
   */
  pk_field: string;
  permissions: Permissions;
  columns: ColumnDescriptor[];
  /**
   * `ModelAdmin.list_display_links` (#251 / #666): the column name(s) whose
   * cell links to the change page. The backend resolves
   * `get_list_display_links` (which defaults to the first column) and emits
   * the result; an empty array means `list_display_links = None` — *no*
   * column links and the rows are not clickable. Only string column names
   * round-trip (callable `list_display` entries are dropped backend-side).
   * Optional for back-compat with a pre-1.6.0 backend: when absent the SPA
   * falls back to linking the first non-pk column (legacy behaviour).
   */
  list_display_links?: string[];
  search_fields: string[];
  /** `ModelAdmin.search_help_text` — shown under the search box (#445).
   *  Empty string when unset. */
  search_help_text: string;
  /** `list_filter` descriptors; always present (empty array when none). */
  filters: FilterDescriptor[];
  /** Bulk actions from `ModelAdmin.actions`; always present. */
  actions: ActionDescriptor[];
  /** Present only when the admin declares `date_hierarchy`. */
  date_hierarchy?: DateHierarchy;
  page: number;
  page_size: number;
  /** Row count after search / filter / date narrowing. */
  total: number;
  /**
   * Unfiltered base count (`ModelAdmin.get_queryset`). Equals `total` when
   * the list isn't narrowed; `null` when the admin sets
   * `show_full_result_count = False`. The SPA shows "<total> of
   * <full_count>" when they differ (`show_full_result_count` parity).
   */
  full_count: number | null;
  /**
   * `ModelAdmin.list_max_show_all` (default 200). The SPA offers a
   * "Show all N" control only when `total` is at/below this cap; sending
   * `?all` then drops pagination and returns every row (Django changelist
   * parity, #385). Above the cap the backend ignores `?all`.
   */
  list_max_show_all: number;
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
  /**
   * Optional control override (see `WidgetHint`). Absent for the default
   * control implied by `type`. `password` additionally means the backend
   * has redacted `value` (it ships `null`).
   */
  widget?: WidgetHint;
  /**
   * Dotted Python path of the bound form widget's class (api 1.3.0+),
   * present only when `widget` is `"custom"`. The SPA dispatches to a
   * consumer-registered widget via `registerFieldWidget(widget_class,
   * …)`; falls back to the default control + an "open in legacy admin"
   * note when no registration matches (#625).
   */
  widget_class?: string;
}

export interface FieldsetDescriptor {
  title: string | null;
  /** Row-flattened field list (back-compat). Prefer `field_rows`. */
  fields: string[];
  /**
   * Field grouping by display row (#382): each inner array is one row,
   * preserving Django's `fields=(("first","last"),"email")` tuple
   * grouping. Optional for back-compat — when absent, render one field
   * per row from `fields`.
   */
  field_rows?: string[][];
  /**
   * Django fieldset `classes` (e.g. `"collapse"`, `"wide"`). When it
   * includes `"collapse"`, the SPA renders the section collapsed by
   * default. Absent on the flat fallback group.
   */
  classes?: string[];
  /** Optional fieldset help text shown under the section title. */
  description?: string | null;
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
  /**
   * Optional control override, mirroring `FieldDescriptor.widget`. Present
   * only for inline fields the admin masks with `PasswordInput` (#504, the
   * inline-half completion of #522): the value is server-redacted and the
   * SPA masks the input.
   */
  widget?: WidgetHint;
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
  /**
   * The child model's pk field name. When the pk is an explicit field
   * (e.g. a UUIDField) it appears as an inline column; the SPA renders
   * that column without truncation so the identity stays readable
   * (mirrors the list `pk_field`, #418 / #360).
   */
  pk_field: string;
  child: { app_label: string; model_name: string };
  extra: number;
  min_num: number | null;
  max_num: number | null;
  can_view: boolean;
  can_add: boolean;
  can_change: boolean;
  can_delete: boolean;
  /**
   * `InlineModelAdmin.show_change_link` — when true, the SPA renders a
   * per-row link to the child's own change page. Only ever true when the
   * child model is admin-registered (so the link can't 404).
   */
  show_change_link: boolean;
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
  /** Raw `ModelAdmin.save_on_top`: mirror the save-button row at the top
   *  of the form too, matching Django's change-form layout. */
  save_on_top: boolean;
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
  /** "View on site" URL (ModelAdmin.view_on_site → callable result or the
   *  object's get_absolute_url). `null` when not applicable. Optional for
   *  back-compat with older backends. */
  view_on_site_url?: string | null;
  /** Custom admin views reachable via `ModelAdmin.get_urls()` (Issue #439):
   *  object-level tool views (url carries this object's pk) plus any
   *  changelist-level pages. The SPA links out to the Django-rendered
   *  page. Optional/absent when the admin exposes no custom routes. */
  custom_views?: CustomView[];
  /**
   * Object-level change-page actions (#236) — the django-object-actions
   * `change_actions` affordance. Present (possibly `[]`) only when the
   * admin exposes object actions; absent for a plain-Django admin. The
   * SPA renders a button per entry; clicking runs
   * `POST <app>/<model>/<pk>/action/<name>/`.
   */
  object_actions?: ObjectActionDescriptor[];
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
  /**
   * `ModelAdmin.prepopulated_fields` as `{target: [sources]}` (#245). The
   * SPA slugifies the target field from its source fields' values while
   * the user types, until the target is edited by hand. Restricted to
   * rendered, non-readonly targets. Optional for back-compat.
   */
  prepopulated_fields?: Record<string, string[]>;
}

/**
 * Closed widget-kind enum from the form-spec endpoint (rest-api 1.4.0+,
 * `#59`). Derived from each field's *resolved* Django form widget — every
 * stdlib + admin widget maps to one of these, with `custom` for a widget
 * whose class lives outside `django.*`. This is *how* to render a field
 * (the control); `FieldType` is *what* the value is. The SPA maps the
 * relevant kinds onto its existing `WidgetHint` controls; the rest fall
 * back to the control implied by `FieldType`.
 */
export type WidgetKind =
  | 'text'
  | 'textarea'
  | 'number'
  | 'email'
  | 'url'
  | 'password'
  | 'hidden'
  | 'checkbox'
  | 'checkbox-multiple'
  | 'select'
  | 'select-multiple'
  | 'radio'
  | 'date'
  | 'datetime'
  | 'time'
  | 'split-datetime'
  | 'select-date'
  | 'file'
  | 'autocomplete'
  | 'autocomplete-multiple'
  | 'raw-id'
  | 'shuttle'
  | 'custom';

/**
 * The resolved-widget block on a form-spec field. `kind` is the closed
 * enum above; `attrs` carries the widget's HTML attrs (so `formfield_overrides`
 * is visible — a forced `Textarea`'s `{rows: 10}`, a `CharField`'s
 * `{maxlength: 150}`). `widget_class` (+ `template_name`) is present when
 * the widget class lives outside `django.*`, so a consumer-registered
 * renderer (`registerFieldWidget`, #625) can dispatch on it.
 */
export interface WidgetBlock {
  kind: WidgetKind;
  attrs: Record<string, string | number | boolean>;
  widget_class?: string;
  template_name?: string;
}

/**
 * One field in a form-spec payload. Same value vocabulary as
 * `FieldDescriptor` (the backend reuses the detail serializer, so `initial`
 * has the identical shape `FieldDescriptor.value` does — FK `{id,label}`,
 * M2M `[{id,label}]`, a redacted password `null`), plus the closed
 * `widget` block and per-field `errors`.
 */
export interface FormSpecField {
  label: string;
  help_text: string;
  required: boolean;
  readonly: boolean;
  type: FieldType;
  widget: WidgetBlock;
  initial: FieldValue;
  errors: string[];
  choices?: FieldChoice[];
  to?: { app_label: string; model_name: string };
  max_length?: number;
  decimal_places?: number;
}

/**
 * Response of `GET /api/v1/<app>/<model>/<pk>/form-spec/` (or
 * `…/add/form-spec/`) — the ModelAdmin-resolved form (rest-api 1.4.0+,
 * #59). Either the JSON form spec (`renderer: "form-spec"`) or, when the
 * admin overrides `change_form_template` / `add_form_template`, a
 * server-rendered html-fragment the SPA injects in-shell
 * (`renderer: "html-fragment"`, rest-api 1.7.0+, #679).
 */
export interface FormSpecResponse {
  renderer: 'form-spec';
  fieldsets: FieldsetDescriptor[];
  fields: Record<string, FormSpecField>;
  /** Dotted path of the resolved `Form` class — changes when a
   *  request-aware `get_form` switched form by querystring/user. */
  variant: string;
  /**
   * `ModelAdmin.prepopulated_fields` as `{target: [sources]}` (#245 / #664).
   * Emitted by the form-spec endpoint only on the ADD form (rest-api 1.6.0+),
   * matching Django's slugify-on-keystroke behaviour for a *new* object. The
   * SPA slugifies the target from its sources as the user types, until the
   * target is hand-edited. Restricted backend-side to rendered, non-readonly
   * targets. Optional/absent on the change form and on a pre-1.6.0 backend.
   */
  prepopulated_fields?: Record<string, string[]>;
}

/**
 * One Django `messages` entry surfaced from a server-rendered html-fragment
 * round-trip (#679). `level` is Django's level tag (`success` / `error` /
 * `warning` / `info` / `debug`); `text` is the rendered message. The SPA
 * toasts these via the shared `toastMessages` adapter.
 */
export interface FragmentMessage {
  level: string;
  text: string;
}

/**
 * Escape hatch for a custom `change_form_template` / `add_form_template`
 * admin (rest-api 1.7.0+, #679). The backend renders the admin's real
 * change/add view SERVER-SIDE, strips the admin chrome, and returns the
 * content-block HTML for the SPA to inject inside its own shell — no iframe,
 * so no `X-Frame-Options` / `SameSite` failure mode.
 *
 * `html` is TRUSTED: it is the integrator's own admin template, rendered by
 * their backend behind the same auth as `/admin/`, and is injected verbatim
 * (inline `<script>` / `<style>` execute — that's the contract; see
 * `HtmlFragment.tsx` for the trust boundary). `submit_url` + `method` +
 * `csrf_token` wire the injected `<form>`; `messages` are toasted.
 */
export interface HtmlFragmentResponse {
  renderer: 'html-fragment';
  html: string;
  csrf_token: string;
  submit_url: string;
  method: string;
  messages: FragmentMessage[];
}

/**
 * The POST round-trip (`POST <app>/<model>/<pk>/change/?<qs>`, #679) returns
 * this when the legacy `change_view` redirects on success. `to` is the legacy
 * target already mapped onto the SPA prefix by the backend (e.g.
 * `/admin2/jobs/job/1/change/`); the SPA `navigate(to)`s it (never a full
 * `window.location` reload). `messages` are toasted.
 */
export interface RedirectResponse {
  renderer: 'redirect';
  to: string;
  messages: FragmentMessage[];
}

/** GET `…/form-spec/` resolves to one of these (#679: no more `legacy-iframe`). */
export type FormSpecPayload = FormSpecResponse | HtmlFragmentResponse;

/**
 * POST `…/<pk>/change/` (the html-fragment round-trip, #679) resolves to
 * another html-fragment (validation errors / self-redirect re-render) or a
 * redirect (success).
 */
export type ChangePostPayload = HtmlFragmentResponse | RedirectResponse;

/**
 * One object-history entry (Django LogEntry) — `GET <app>/<model>/<pk>/history/`.
 * `action` is `addition` / `change` / `deletion` / `unknown`;
 * `change_message_human` is Django's rendered summary.
 */
export interface HistoryEntry {
  id: number;
  action: string;
  action_time: string;
  user: { id: number; label: string } | null;
  change_message_human: string;
  change_message_structured?: unknown;
}

/** Paginated object-history timeline (#244). */
export interface HistoryResponse {
  object: { pk: number | string; label: string };
  entries: HistoryEntry[];
  page: number;
  page_size: number;
  total: number;
  num_pages: number;
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
// A scalar field value, OR a list of related pks for a ManyToMany write
// (Issue #240). The backend M2M write path accepts a list of pks
// (writes.py `_coerce` → `form.save_m2m()`); the SPA sends `[pk, ...]`.
export type WriteValue = string | number | boolean | null | Array<string | number>;

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
