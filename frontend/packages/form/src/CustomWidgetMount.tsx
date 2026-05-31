// CustomWidgetMount — React adapter for the consumer-supplied
// vanilla mount-fn plugin protocol (#625). Bridges the SPA's
// controlled-form world (value + onChange every render) to the
// imperative DOM world of a `function mount(container, props)`
// contract.
//
// Why this layer:
// - The SPA's React is bundled into the wheel; exposing it on a
//   global so consumer React components can use it is fragile
//   across rebuilds.
// - A vanilla mount-fn contract keeps the consumer free to use
//   any framework (jQuery, Stimulus, mini-React, vanilla DOM).
// - The mount fn is called once on mount with the initial props;
//   value changes invoked from inside the widget (via
//   `props.onChange`) flow through React's normal re-render path.
//   Successive mounts after a re-render don't fire — React's
//   useEffect with `[]` deps mounts exactly once.

import { useEffect, useRef } from 'react';

import type { WriteValue } from '@dar/data';
import type { CustomWidgetSpec } from '@dar/ui';

interface CustomWidgetMountProps {
  spec: CustomWidgetSpec;
  widgetClass: string;
  value: WriteValue;
  onChange: (next: WriteValue) => void;
  error: string[] | undefined;
}

export function CustomWidgetMount({
  spec,
  widgetClass,
  value,
  onChange,
  error,
}: CustomWidgetMountProps): JSX.Element {
  const ref = useRef<HTMLDivElement>(null);
  // Latest props the widget needs to see at re-render time. The
  // mount fn captured the FIRST onChange; subsequent React renders
  // would close over a stale onChange unless we forward via a
  // ref. The widget reads through this ref each time it emits.
  const latestProps = useRef({ value, onChange, error, widgetClass });
  latestProps.current = { value, onChange, error, widgetClass };

  useEffect(() => {
    if (!ref.current) return undefined;
    const container = ref.current;
    // Mount with stable proxies — the widget's mount fn captures
    // these once; the wrappers read through latestProps.current so
    // every emit and every value-read sees the freshest binding.
    const cleanup = spec.mount(container, {
      get value() {
        return latestProps.current.value;
      },
      onChange: (next) => latestProps.current.onChange(next),
      get error() {
        return latestProps.current.error;
      },
      get widgetClass() {
        return latestProps.current.widgetClass;
      },
    });
    return () => {
      if (typeof cleanup === 'function') cleanup();
      // Defensive: if the widget didn't fully tear down its DOM,
      // wipe the container so a re-mount starts clean. The mount
      // fn is the source of truth; this is a last-resort backstop.
      container.innerHTML = '';
    };
    // Intentional: mount-once contract. Re-mounting on every value
    // change would defeat the imperative widget's own state
    // management. The latestProps ref pattern (above) forwards
    // value / onChange / error to the widget without re-mounting.
  }, [spec]);

  return (
    <div
      ref={ref}
      data-custom-widget-class={widgetClass}
      className="rounded border border-gray-300 p-2"
    />
  );
}
