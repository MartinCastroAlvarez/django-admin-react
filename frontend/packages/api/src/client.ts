// HTTP client for the django-admin-react JSON API.
//
// Single source of network truth. Other packages MUST NOT call
// `fetch` directly; they go through @dar/data which goes through
// here. See `CLAUDE.md` §7.

import type {
  ActionRunResponse,
  AutocompleteResponse,
  AddFormResponse,
  CreatePayload,
  CreateResponse,
  DeletePreviewResponse,
  DetailResponse,
  FieldErrorEnvelope,
  ListResponse,
  LoginResponse,
  RegistryResponse,
  UpdatePayload,
} from './contract';

export interface ApiClientConfig {
  /**
   * Absolute path the package is mounted at, e.g. `/admin-react/`.
   * Reported by the backend in the `registry` response and reused as
   * the base for all subsequent calls.
   */
  mount: string;
  /**
   * Fetch implementation; defaults to global fetch. Overridable for
   * tests.
   */
  fetchImpl?: typeof fetch;
  /**
   * Cookie name Django uses for the CSRF token. Default: `csrftoken`.
   */
  csrfCookieName?: string;
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
  private readonly fetchImpl: typeof fetch;
  private readonly csrfCookieName: string;

  constructor(config: ApiClientConfig) {
    this.mount = config.mount.endsWith('/') ? config.mount : `${config.mount}/`;
    this.fetchImpl = config.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.csrfCookieName = config.csrfCookieName ?? 'csrftoken';
  }

  private url(path: string): string {
    const trimmed = path.startsWith('/') ? path.slice(1) : path;
    return `${this.mount}api/v1/${trimmed}`;
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

  list(
    appLabel: string,
    modelName: string,
    params: {
      q?: string;
      page?: number;
      page_size?: number;
      ordering?: string;
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
   * End the current session via the package's logout endpoint
   * (`POST /api/v1/logout/`, `api/views/auth.py`) — a thin JSON shell over
   * Django's own `logout` that flushes the session server-side. Idempotent
   * (logging out while already anonymous is a harmless 200). CSRF is
   * enforced by the middleware, same as `login()`.
   */
  logout(): Promise<{ detail: string }> {
    return this.request<{ detail: string }>('POST', 'logout/', {});
  }

  /** The create-form schema for a NEW object (GET <app>/<model>/add/). */
  addForm(appLabel: string, modelName: string): Promise<AddFormResponse> {
    return this.request<AddFormResponse>('GET', `${appLabel}/${modelName}/add/`);
  }

  create(appLabel: string, modelName: string, payload: CreatePayload): Promise<CreateResponse> {
    return this.request<CreateResponse>('POST', `${appLabel}/${modelName}/`, payload);
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
