// HTTP client for the django-admin-react JSON API.
//
// Single source of network truth. Other packages MUST NOT call
// `fetch` directly; they go through @dar/data which goes through
// here. See `CLAUDE.md` §7.

import type {
  ActionRunResponse,
  AutocompleteResponse,
  AddFormResponse,
  BulkUpdateEntry,
  BulkUpdateResponse,
  CreatePayload,
  CreateResponse,
  DeletePreviewResponse,
  DetailResponse,
  FieldErrorEnvelope,
  FormSpecPayload,
  HistoryResponse,
  ListResponse,
  LoginResponse,
  RecentActionsResponse,
  RegistryResponse,
  UpdatePayload,
} from './contract';

export interface ApiClientConfig {
  /**
   * Absolute path the package is mounted at, e.g. `/admin-react/`.
   * Used as the router basename and as the default API-prefix base when
   * `apiPrefix` is not supplied.
   */
  mount: string;
  /**
   * Absolute URL prefix for every JSON request (#559). Lets the consumer
   * point the SPA at a separately-mounted `django-admin-rest-api`
   * instead of the inline `<mount>api/v1/` include. When omitted, falls
   * back to `<mount>api/v1/` — the historical behaviour, unchanged for
   * existing consumers.
   */
  apiPrefix?: string;
  /**
   * Fetch implementation; defaults to global fetch. Overridable for
   * tests.
   */
  fetchImpl?: typeof fetch;
  /**
   * Cookie name Django uses for the CSRF token. Default: `csrftoken`.
   */
  csrfCookieName?: string;
  /**
   * Called when a request fails with a *session-level* auth error: a
   * `401`, or a `403` whose envelope code is `session_expired` (the
   * operator's session went away mid-session — logout elsewhere,
   * server-side flush, age expiry). The app wires this to a
   * redirect-to-login so the operator isn't dead-ended on an error
   * screen and returns to the same path after sign-in (api-contract
   * §6.1 / §10.1, issue #414). It is **not** called for a plain
   * `forbidden` 403 (signed-in but lacking a permission) — that stays
   * on the page as an inline error.
   */
  onAuthFailure?: () => void;
}

export class ApiError extends Error {
  status: number;
  envelope: FieldErrorEnvelope | null;
  constructor(status: number, envelope: FieldErrorEnvelope | null, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.envelope = envelope;
  }
}

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

export class ApiClient {
  private readonly mount: string;
  private readonly apiPrefix: string;
  private readonly fetchImpl: typeof fetch;
  private readonly csrfCookieName: string;
  private readonly onAuthFailure: (() => void) | undefined;

  constructor(config: ApiClientConfig) {
    this.mount = config.mount.endsWith('/') ? config.mount : `${config.mount}/`;
    // Default the API prefix to `<mount>api/v1/` so behaviour is
    // unchanged for consumers who don't set `DJANGO_ADMIN_REACT
    // ["API_URL_PREFIX"]` (#559). Always ends with "/" so concat is
    // safe in `url()`.
    const rawPrefix = config.apiPrefix ?? `${this.mount}api/v1/`;
    this.apiPrefix = rawPrefix.endsWith('/') ? rawPrefix : `${rawPrefix}/`;
    this.fetchImpl = config.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.csrfCookieName = config.csrfCookieName ?? 'csrftoken';
    this.onAuthFailure = config.onAuthFailure;
  }

  /**
   * A session-level auth failure that should bounce the operator to
   * login — a `401`, or a `403` flagged `session_expired`. A plain
   * `forbidden` 403 (authenticated but unauthorized) is deliberately
   * excluded so per-permission denials render inline instead (§6.1).
   */
  private isSessionAuthFailure(status: number, envelope: FieldErrorEnvelope | null): boolean {
    if (status === 401) return true;
    return status === 403 && envelope?.error?.code === 'session_expired';
  }

  private url(path: string): string {
    const trimmed = path.startsWith('/') ? path.slice(1) : path;
    return `${this.apiPrefix}${trimmed}`;
  }

  private csrfToken(): string | null {
    if (typeof document === 'undefined') return null;
    const prefix = `${this.csrfCookieName}=`;
    for (const part of document.cookie.split(';')) {
      const trimmed = part.trim();
      if (trimmed.startsWith(prefix)) {
        return decodeURIComponent(trimmed.slice(prefix.length));
      }
    }
    return null;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
    };
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    if (!SAFE_METHODS.has(method)) {
      const token = this.csrfToken();
      if (token) headers['X-CSRFToken'] = token;
    }

    const init: RequestInit = {
      method,
      credentials: 'include',
      headers,
    };
    if (body !== undefined) {
      init.body = JSON.stringify(body);
    }
    const response = await this.fetchImpl(this.url(path), init);

    if (response.status === 204) {
      return undefined as unknown as T;
    }

    const text = await response.text();
    let parsed: unknown = null;
    if (text) {
      try {
        parsed = JSON.parse(text);
      } catch {
        // Fall through with parsed === null.
      }
    }

    if (!response.ok) {
      const envelope = (parsed ?? null) as FieldErrorEnvelope | null;
      // Mid-session auth loss: hand off to the redirect-to-login hook
      // *before* throwing, so the operator recovers instead of staring
      // at a dead-end error (#414). Still throws so callers' error
      // states stay consistent.
      if (this.isSessionAuthFailure(response.status, envelope)) {
        this.onAuthFailure?.();
      }
      throw new ApiError(
        response.status,
        envelope,
        envelope?.error?.message ?? `HTTP ${response.status}`,
      );
    }

    return parsed as T;
  }

  getRegistry(): Promise<RegistryResponse> {
    return this.request<RegistryResponse>('GET', 'registry/');
  }

  /** The signed-in user's recent admin actions for the index panel (#502). */
  getRecentActions(limit?: number): Promise<RecentActionsResponse> {
    const path = limit ? `recent-actions/?limit=${encodeURIComponent(String(limit))}` : 'recent-actions/';
    return this.request<RecentActionsResponse>('GET', path);
  }

  list(
    appLabel: string,
    modelName: string,
    params: {
      q?: string;
      page?: number;
      page_size?: number;
      ordering?: string;
      /**
       * "Show all" flag (Django's `ALL_VAR`, #385). When true the request
       * sends `?all` and the backend drops pagination — returning every
       * row — provided `total <= list_max_show_all`.
       */
      all?: boolean;
      /**
       * Arbitrary `list_filter` query params keyed by the descriptor's
       * `name` (e.g. `{ created_at_filter: '7_days' }`). Empty-string /
       * null values are omitted so clearing a filter drops it.
       */
      filters?: Record<string, string | null | undefined>;
    } = {},
  ): Promise<ListResponse> {
    const search = new URLSearchParams();
    if (params.q) search.set('q', params.q);
    if (params.page) search.set('page', String(params.page));
    if (params.page_size) search.set('page_size', String(params.page_size));
    if (params.ordering) search.set('ordering', params.ordering);
    // Bare `?all` (no value), matching Django's changelist ALL_VAR.
    if (params.all) search.set('all', '');
    for (const [key, value] of Object.entries(params.filters ?? {})) {
      if (value !== undefined && value !== null && value !== '') {
        search.set(key, value);
      }
    }
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : '';
    return this.request<ListResponse>('GET', `${appLabel}/${modelName}/${suffix}`);
  }

  detail(appLabel: string, modelName: string, pk: string | number): Promise<DetailResponse> {
    return this.request<DetailResponse>('GET', `${appLabel}/${modelName}/${pk}/`);
  }

  /**
   * Authenticate via the package's React-login endpoint (contract §7,
   * Issue #167). A thin JSON shell over Django's own
   * `authenticate`/`login` (`api/views/auth.py`) — on success the
   * session cookie is set and the user block returned; a bad login is
   * a generic 403 surfaced as an `ApiError` (no user-enumeration
   * oracle). CSRF is enforced by the middleware.
   */
  login(username: string, password: string): Promise<LoginResponse> {
    return this.request<LoginResponse>('POST', 'login/', { username, password });
  }

  /**
   * End the current session (contract §7, Issue #167). A thin JSON shell
   * over Django's own `logout` (`api/views/auth.py`) — flushes the
   * session server-side and clears the auth cookie. Idempotent: logging
   * out while already anonymous is a harmless `200`, and because POST is
   * unsafe, CSRF is enforced (a forged cross-site logout can't drop a
   * victim's session). The caller is responsible for purging any
   * client-side cache (see `@dar/data` `purgeLocalCache`) and reloading.
   */
  logout(): Promise<{ detail: string }> {
    return this.request<{ detail: string }>('POST', 'logout/', {});
  }

  /** The create-form schema for a NEW object (GET <app>/<model>/add/). */
  addForm(appLabel: string, modelName: string): Promise<AddFormResponse> {
    return this.request<AddFormResponse>('GET', `${appLabel}/${modelName}/add/`);
  }

  /**
   * The ModelAdmin-resolved form spec (rest-api 1.4.0+, #59): request-aware
   * `get_form` / `get_fieldsets` / `get_readonly_fields` with a closed
   * `widget.kind` per field, or a `legacy-iframe` pointer. Pass `pk` for
   * the change form, omit it for the add form. `query` is the original
   * change-form querystring (forwarded so a request-aware `get_form` that
   * branches on `?variant=…` resolves the matching form).
   */
  formSpec(
    appLabel: string,
    modelName: string,
    pk?: string | number,
    query?: string,
  ): Promise<FormSpecPayload> {
    const base =
      pk === undefined || pk === null || pk === ''
        ? `${appLabel}/${modelName}/add/form-spec/`
        : `${appLabel}/${modelName}/${pk}/form-spec/`;
    const qs = query ? (query.startsWith('?') ? query : `?${query}`) : '';
    return this.request<FormSpecPayload>('GET', `${base}${qs}`);
  }

  /** Object-history timeline (GET <app>/<model>/<pk>/history/) — #244. */
  history(
    appLabel: string,
    modelName: string,
    pk: string | number,
    page = 1,
  ): Promise<HistoryResponse> {
    const qs = page > 1 ? `?page=${page}` : '';
    return this.request<HistoryResponse>('GET', `${appLabel}/${modelName}/${pk}/history/${qs}`);
  }

  create(appLabel: string, modelName: string, payload: CreatePayload): Promise<CreateResponse> {
    return this.request<CreateResponse>('POST', `${appLabel}/${modelName}/`, payload);
  }

  /** Bulk PATCH for inline list_editable edits (#243) — PATCH <app>/<model>/bulk/. */
  bulkUpdate(
    appLabel: string,
    modelName: string,
    updates: BulkUpdateEntry[],
  ): Promise<BulkUpdateResponse> {
    return this.request<BulkUpdateResponse>('PATCH', `${appLabel}/${modelName}/bulk/`, { updates });
  }

  update(
    appLabel: string,
    modelName: string,
    pk: string | number,
    payload: UpdatePayload,
  ): Promise<DetailResponse> {
    return this.request<DetailResponse>('PATCH', `${appLabel}/${modelName}/${pk}/`, payload);
  }

  delete(appLabel: string, modelName: string, pk: string | number): Promise<void> {
    return this.request<void>('DELETE', `${appLabel}/${modelName}/${pk}/`);
  }

  /**
   * Cascade preview for a delete (contract §5.3) — what else gets
   * removed, what's PROTECT-blocked, and which extra delete perms are
   * needed. The SPA shows this before invoking `delete()` so a single
   * click can't silently cascade rows the operator never saw (#153).
   * Read-only; never mutates.
   */
  deletePreview(
    appLabel: string,
    modelName: string,
    pk: string | number,
  ): Promise<DeletePreviewResponse> {
    return this.request<DeletePreviewResponse>(
      'GET',
      `${appLabel}/${modelName}/${pk}/delete-preview/`,
    );
  }

  /**
   * Run a `ModelAdmin` action over the selected rows (contract §5.4).
   * The backend re-resolves the action name through
   * `get_actions(request)` — the SPA name is never trusted as a
   * callable lookup — and runs it over
   * `get_queryset(request).filter(pk__in=pks)`.
   */
  runAction(
    appLabel: string,
    modelName: string,
    actionName: string,
    pks: Array<string | number>,
    confirmed = true,
  ): Promise<ActionRunResponse> {
    return this.request<ActionRunResponse>(
      'POST',
      `${appLabel}/${modelName}/actions/${actionName}/`,
      { pks, confirmed },
    );
  }

  // `runObjectAction` is intentionally not on the HTTP client anymore
  // (v1.4.8 / #603 revised). The dedicated `/<pk>/action/<name>/`
  // endpoint was removed in api 1.0.5 — detail-page actions now go
  // through `runAction(name, [pk])` against the existing changelist
  // runner. The legacy `runObjectAction` helper still exists in
  // `@dar/data`'s mutations.ts, but it delegates to `runAction`
  // internally rather than hitting a separate endpoint.

  /**
   * Typeahead for a high-cardinality FK picker (contract §3.2). The
   * `appLabel`/`modelName` are the **target** model's; results are
   * powered by the target admin's `search_fields` /
   * `get_search_results`. Returns `{ results: [{id, label}], ... }`.
   */
  autocomplete(
    appLabel: string,
    modelName: string,
    q: string,
    page = 1,
  ): Promise<AutocompleteResponse> {
    const search = new URLSearchParams();
    if (q) search.set('q', q);
    if (page > 1) search.set('page', String(page));
    const qs = search.toString();
    return this.request<AutocompleteResponse>(
      'GET',
      `${appLabel}/${modelName}/autocomplete/${qs ? `?${qs}` : ''}`,
    );
  }
}
