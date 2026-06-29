// HtmlFragment — render a server-rendered custom change form INSIDE the SPA
// shell (#679). Replaces the old legacy-iframe escape hatch entirely.
//
// When a ModelAdmin overrides `change_form_template` (or renders a custom
// template from a `change_view` branch like `?run_custom=1`), the JSON
// form-spec can't reproduce the form, so the backend (rest-api 1.7.0+, #75)
// renders the admin's real view server-side, strips the admin chrome, and
// returns `{renderer: "html-fragment", html, csrf_token, submit_url, method,
// messages}`. We inject `html` into the content area while the breadcrumb,
// sidebar, title, and toolbar stay React-rendered — no iframe, so no
// `X-Frame-Options` / `SameSite` failure mode ever again.
//
// TRUST BOUNDARY (#679): `html` is TRUSTED. It is the integrator's own admin
// template, rendered by their backend behind the same auth as `/admin/`, and
// delivered over the same authenticated, same-origin API as every other
// payload. We DELIBERATELY do not sanitise it: the custom form's inline
// `<script>` (dual-listbox handlers, drag-and-drop, embedded widgets) and
// `<style>` are part of the form contract and MUST run. This is the same
// trust the integrator already places in their legacy admin. The fragment is
// never cross-origin and never attacker-controlled in a correctly-deployed
// admin; the threat model is identical to the legacy `/admin/` page itself.
//
// Because React's `dangerouslySetInnerHTML` does NOT execute `<script>`
// elements parsed from a string (the HTML spec disables scripts inserted via
// innerHTML), we parse the fragment, mount the non-script markup, then clone
// each `<script>` into a fresh element and append it so the browser executes
// it — the dual-listbox JS only works because of this re-execution step.

import { useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

import { type ChangePostPayload, type HtmlFragmentResponse, useApiClient } from '@dar/data';
import { Card } from '@dar/ui';

import { toastMessages, useToast } from '../../toast';

export interface HtmlFragmentProps {
  fragment: HtmlFragmentResponse;
  appLabel: string;
  modelName: string;
  pk: string;
  /** Original change-form querystring (e.g. `run_custom=1`), forwarded so the
   *  request-aware `change_view` resolves the same branch on POST. */
  query?: string;
}

/**
 * Re-execute `<script>` elements within an injected fragment.
 *
 * `dangerouslySetInnerHTML` / `innerHTML` parse `<script>` tags into inert
 * elements — the HTML parser flags scripts inserted that way as
 * "already started", so they never run. To make the integrator's inline JS
 * run, we walk the injected scripts, build a fresh `<script>` for each
 * (copying attributes + text), and swap it in. A newly *created* and
 * *inserted* script element executes per the DOM spec.
 */
// Event names an injected script may use to defer its init until "page ready".
const READY_EVENTS = new Set(['DOMContentLoaded', 'readystatechange']);

function executeScripts(container: HTMLElement): void {
  // A very common admin-template idiom (Django's own, and what most hand-rolled
  // dual-listbox / drag-and-drop forms use) wires every control inside
  // `document.addEventListener('DOMContentLoaded', () => { … })`. By the time
  // the SPA injects this fragment, the page's real `DOMContentLoaded`/`load`
  // fired long ago and will never fire again, so such a handler would register
  // but never run — leaving every button dead (#693).
  //
  // We can't just re-dispatch the events globally: that re-invokes EVERY
  // `DOMContentLoaded` listener on the page, including stale ones from
  // previously-injected fragments (whose DOM is gone → they throw) and the
  // app's own. Instead, while the fragment's inline scripts run, we intercept
  // their `DOMContentLoaded`/`load` registrations, keep them OFF the global
  // targets (no leak, no re-fire on the next fragment), and invoke just those
  // captured handlers once — exactly the "page is ready" signal they wait for.
  const deferred: EventListener[] = [];
  const capture =
    (real: typeof document.addEventListener, names: Set<string>) =>
    (type: string, listener: EventListenerOrEventListenerObject, options?: unknown): void => {
      if (names.has(type) && typeof listener === 'function') {
        deferred.push(listener as EventListener);
        return;
      }
      (real as (t: string, l: EventListenerOrEventListenerObject, o?: unknown) => void)(
        type,
        listener,
        options,
      );
    };

  const origDocAdd = document.addEventListener;
  const origWinAdd = window.addEventListener;
  document.addEventListener = capture(origDocAdd.bind(document), READY_EVENTS) as typeof document.addEventListener;
  window.addEventListener = capture(origWinAdd.bind(window), new Set(['load'])) as typeof window.addEventListener;

  try {
    const scripts = Array.from(container.querySelectorAll('script'));
    for (const old of scripts) {
      const replacement = document.createElement('script');
      for (const attr of Array.from(old.attributes)) {
        replacement.setAttribute(attr.name, attr.value);
      }
      replacement.text = old.textContent ?? '';
      // Inline scripts execute synchronously on insertion, so their
      // `addEventListener` calls hit our interceptor above before the `finally`
      // restores the originals.
      old.replaceWith(replacement);
    }
  } finally {
    document.addEventListener = origDocAdd;
    window.addEventListener = origWinAdd;
  }

  // Fire the captured "ready" handlers once, scoped to this fragment.
  const readyEvent = new Event('DOMContentLoaded');
  for (const fn of deferred) {
    try {
      fn.call(document, readyEvent);
    } catch (err) {
      // A broken init handler must not take down the SPA; the rest of the
      // form (and other handlers) should still wire up.
      console.error('[django-admin-react] custom-form init handler threw', err);
    }
  }
}

export function HtmlFragment({ fragment, appLabel, modelName, pk, query }: HtmlFragmentProps) {
  const client = useApiClient();
  const navigate = useNavigate();
  const toast = useToast();

  const hostRef = useRef<HTMLDivElement | null>(null);
  // The fragment currently injected. Held in a ref (not state) so the submit
  // handler always reads the live fragment after a validation re-inject
  // without re-binding the form listener.
  const fragmentRef = useRef<HtmlFragmentResponse>(fragment);
  // Toast the messages from each payload exactly once (success on first load,
  // errors on a validation round-trip). Tracks the last-toasted reference.
  const toastedRef = useRef<HtmlFragmentResponse['messages'] | null>(null);

  // Inject markup + (re-)wire the form. Factored out so a validation-error
  // round-trip can re-inject without a full SPA route change (#679).
  const inject = useCallback(
    (frag: HtmlFragmentResponse) => {
      const host = hostRef.current;
      if (!host) return;
      fragmentRef.current = frag;
      // Replace the previous fragment wholesale.
      host.innerHTML = frag.html;
      // Make inline <script> run (innerHTML-parsed scripts are inert).
      executeScripts(host);

      // Surface this payload's Django messages as toasts, once.
      if (frag.messages.length > 0 && toastedRef.current !== frag.messages) {
        toastedRef.current = frag.messages;
        toastMessages(
          toast,
          frag.messages.map((m) => ({ level: m.level, message: m.text })),
        );
      }
    },
    [toast],
  );

  // Submit handler for the injected <form>. Captured-phase listener on the
  // host so it sees the submit before the browser performs a native
  // navigation, which we prevent.
  const onSubmit = useCallback(
    (event: SubmitEvent) => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement)) return;
      event.preventDefault();
      const frag = fragmentRef.current;
      const body = new FormData(form);
      void (async () => {
        let result: ChangePostPayload;
        try {
          result = await client.submitChangeFragment({
            appLabel,
            modelName,
            pk,
            query: query ?? '',
            body,
            csrfToken: frag.csrf_token,
            method: frag.method,
          });
        } catch {
          toast.error('Could not submit the form. Please try again.');
          return;
        }
        if (result.renderer === 'redirect') {
          // Toast first (the redirect tears down this component), then SPA
          // navigate — never a window.location reload.
          if (result.messages.length > 0) {
            toastMessages(
              toast,
              result.messages.map((m) => ({ level: m.level, message: m.text })),
            );
          }
          navigate(result.to);
          return;
        }
        // Another html-fragment → validation errors / self-redirect re-render.
        // Re-inject in place, preserving the SPA route.
        inject(result);
      })();
    },
    [client, appLabel, modelName, pk, query, navigate, toast, inject],
  );

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;
    inject(fragment);
    host.addEventListener('submit', onSubmit, true);
    return () => {
      host.removeEventListener('submit', onSubmit, true);
    };
    // `inject` / `onSubmit` are stable across renders (their deps are stable);
    // re-run only when the initial fragment changes (a new edit-mode entry).
  }, [fragment, inject, onSubmit]);

  return (
    <Card>
      {/* The server-rendered custom form, injected in-shell. `data-testid`
          lets the snapshot/interaction test locate the host. */}
      <div ref={hostRef} data-testid="html-fragment-host" />
    </Card>
  );
}
