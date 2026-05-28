// ResetButton (#590) — shared "return to defaults" affordance for the
// list-page filter row ("Clear all") and the Column-Layout modal
// ("Reset"). Both call sites want the same UX primitive: a ghost-styled
// button with optional leading icon, a pending state, and a disabled
// tooltip when there is nothing to reset.
//
// Lives in @dar/ui so future "reset" surfaces (saved searches, sidebar
// customizations, etc.) inherit the same visual + a11y contract by
// construction. The label and icon are configurable per call site so
// the filter row can keep saying "Clear all" with the `X` icon while
// the modal says "Reset" with the curved-arrow icon.
//
// Icon-agnostic: callers pass the icon node themselves so @dar/ui
// stays free of an icon-library dep (matches the rest of the package).

import { cloneElement, isValidElement, useState, type ReactNode } from 'react';

export interface ResetButtonProps {
  /** Is the underlying state actually customised? Disables the button
   *  with a tooltip when false so the affordance stays discoverable. */
  isDirty: boolean;
  /** Run the reset. Promise-returning calls show a pending state; a
   *  synchronous return runs through the same code path and the
   *  finally branch flushes instantly. */
  onReset: () => Promise<void> | void;
  /** Visible label. Default "Reset". */
  label?: string;
  /** Tooltip shown when `isDirty` is false. */
  disabledHint?: string;
  /** Leading icon. If a React element that takes `className`, the
   *  button passes `animate-spin` while a promise-returning onReset
   *  is in flight (the lucide convention). Pass `null` to opt out. */
  icon?: ReactNode;
  /** Extra classes — kept narrow so the visual contract stays uniform. */
  className?: string;
  /** `title` for the trigger button when enabled. */
  title?: string;
  /** Optional content rendered after the label (e.g. a count chip). */
  trailing?: ReactNode;
}

export function ResetButton({
  isDirty,
  onReset,
  label = 'Reset',
  disabledHint = 'Already at default',
  icon = null,
  className,
  title,
  trailing,
}: ResetButtonProps) {
  const [pending, setPending] = useState(false);
  const disabled = !isDirty || pending;

  async function run(): Promise<void> {
    if (disabled) return;
    setPending(true);
    try {
      await onReset();
    } finally {
      setPending(false);
    }
  }

  const tooltip = disabled && !pending ? disabledHint : title;

  // If the caller's icon is a valid element that accepts a `className`,
  // augment it with `animate-spin` during a pending promise — the
  // lucide-react / heroicons convention. Bail out for non-elements
  // (strings, fragments, null).
  const renderedIcon =
    pending && isValidElement<{ className?: string }>(icon)
      ? cloneElement(icon, {
          className: `${icon.props.className ?? ''} animate-spin`.trim(),
        })
      : icon;

  return (
    <button
      type="button"
      onClick={() => {
        void run();
      }}
      disabled={disabled}
      title={tooltip}
      className={[
        'inline-flex shrink-0 items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm',
        disabled
          ? 'cursor-not-allowed text-gray-400'
          : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
        className ?? '',
      ].join(' ')}
    >
      {renderedIcon}
      <span>{pending ? `${label}…` : label}</span>
      {trailing}
    </button>
  );
}
