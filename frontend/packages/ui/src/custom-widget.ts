// Custom widget plugin protocol (#625).
//
// Lets a consumer ship a small JS module that renders their own
// editor for a Django ``formfield_overrides`` widget the SPA
// doesn't natively render. The wire-side half (api 1.3.0+) emits
// ``widget: "custom"`` plus ``widget_class: "<dotted.Python.Path>"``
// on any field whose bound form widget class lives outside
// ``django.*`` — this module is the SPA-side dispatcher.
//
// Consumer contract:
//
//   // Loaded BEFORE the SPA bundle (via a regular `<script>` tag
//   // in your custom `change_form_template`, or via a shared
//   // base template that includes both your widget and the SPA):
//   window.darFieldWidgets = window.darFieldWidgets ?? {};
//   window.darFieldWidgets['mypkg.widgets.MarkdownEditor'] = {
//     mount(container, props) {
//       // Render whatever you want into `container` (vanilla JS,
//       // jQuery, a mini React, …). Read `props.value` for the
//       // current value; call `props.onChange(next)` when the
//       // operator edits; check `props.error` (string[] | undefined)
//       // for validation errors from the last save attempt.
//       // Return a cleanup fn that tears down event listeners
//       // and external resources when the SPA unmounts.
//     }
//   };
//
// Why vanilla JS, not React: the SPA's React is bundled and tree-
// shaken — exposing it on a window global is fragile across bundle
// rebuilds. A vanilla mount-fn contract keeps the consumer's widget
// framework-agnostic (jQuery, Stimulus, mini-React, vanilla DOM
// manipulation all work). The SPA wraps the mount fn in a thin
// React effect that mounts on first paint and cleans up on unmount.

/**
 * Inlined copy of ``@dar/data``'s ``WriteValue`` type. We can't
 * import from ``@dar/data`` here because ``@dar/ui`` is the lowest
 * layer in the workspace and data depends on api / customization
 * (a dep on ``@dar/data`` from ``@dar/ui`` would invert that
 * layering). The type is small and stable; the duplication is
 * deliberate.
 */
type WriteValue = string | number | boolean | null | Array<string | number>;

/** Props passed to a custom widget's mount function. */
export interface CustomWidgetProps {
  /** The current draft value (whatever the operator has typed into
   *  the form so far; matches the SPA's WriteValue vocabulary). */
  value: WriteValue;
  /** Call to emit a new value as the operator interacts. The SPA
   *  re-renders the form with the new value; the widget can stay
   *  controlled (use `value` from the next mount call) or
   *  uncontrolled (manage its own internal state). */
  onChange: (next: WriteValue) => void;
  /** Per-field validation errors from the last save attempt, or
   *  ``undefined`` if no errors. The widget can render its own
   *  error UI; the SPA also renders the errors below the widget
   *  as a fallback so the operator always sees them. */
  error: string[] | undefined;
  /** The dotted class path of the widget — useful when a single
   *  mount fn handles multiple related widgets (color picker for
   *  hex + rgba, e.g.). */
  widgetClass: string;
}

/** A consumer-supplied widget. ``mount`` returns a cleanup fn called
 *  on unmount. */
export interface CustomWidgetSpec {
  mount: (container: HTMLElement, props: CustomWidgetProps) => (() => void) | void;
}

/** Module-level registry the SPA reads at render time. Synced to
 *  ``window.darFieldWidgets`` so consumers can populate it via a
 *  regular ``<script>`` tag that runs before the SPA bundle. */
const registry: Record<string, CustomWidgetSpec> = {};

declare global {
  interface Window {
    darFieldWidgets?: Record<string, CustomWidgetSpec>;
  }
}

/**
 * Register a custom widget. Called either:
 *   - from consumer code, via ``import { registerFieldWidget }
 *     from "django-admin-react/widgets"`` (a future thin npm
 *     publish), OR
 *   - by assigning to ``window.darFieldWidgets['<class>']``
 *     directly (the no-build path).
 *
 * Calling twice with the same class name overwrites; latest wins.
 */
export function registerFieldWidget(widgetClass: string, spec: CustomWidgetSpec): void {
  registry[widgetClass] = spec;
}

/**
 * Look up a registered widget. Returns ``undefined`` when no
 * registration matches — the SPA's caller falls back to the
 * default render in that case.
 *
 * Reads from both the module-level registry (registered via
 * ``registerFieldWidget``) AND the ``window.darFieldWidgets``
 * global (registered via the no-build path). The module wins on
 * conflict — explicit ``registerFieldWidget`` calls are usually
 * later + more intentional.
 */
export function lookupFieldWidget(widgetClass: string): CustomWidgetSpec | undefined {
  return registry[widgetClass] ?? window.darFieldWidgets?.[widgetClass];
}

/** Test-only: wipe the module-level registry between cases. */
export function _resetFieldWidgetRegistryForTests(): void {
  for (const key of Object.keys(registry)) {
    delete registry[key];
  }
}
