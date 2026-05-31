// Lock the custom widget plugin protocol (#625):
//
//   1. `registerFieldWidget(class, spec)` puts a spec in the
//      module-level registry.
//   2. `lookupFieldWidget(class)` returns the registered spec or
//      undefined when nothing matches.
//   3. The window.darFieldWidgets global is a fallback path for
//      consumers shipping a vanilla <script> registration (no
//      build).
//   4. Module-level registry wins over the window global on
//      conflict (explicit `registerFieldWidget` is more intentional
//      than a global assignment).
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  _resetFieldWidgetRegistryForTests,
  lookupFieldWidget,
  registerFieldWidget,
} from './custom-widget';

afterEach(() => {
  _resetFieldWidgetRegistryForTests();
  delete window.darFieldWidgets;
});

describe('registerFieldWidget / lookupFieldWidget', () => {
  it('round-trips a registered widget by class name', () => {
    const spec = { mount: vi.fn() };
    registerFieldWidget('mypkg.MarkdownEditor', spec);
    expect(lookupFieldWidget('mypkg.MarkdownEditor')).toBe(spec);
  });

  it('returns undefined when no registration matches', () => {
    expect(lookupFieldWidget('not.registered')).toBeUndefined();
  });

  it('latest registration wins (re-register overwrites)', () => {
    const first = { mount: vi.fn() };
    const second = { mount: vi.fn() };
    registerFieldWidget('x', first);
    registerFieldWidget('x', second);
    expect(lookupFieldWidget('x')).toBe(second);
  });
});

describe('window.darFieldWidgets fallback (no-build path)', () => {
  it('reads from window.darFieldWidgets when the module registry is empty', () => {
    const spec = { mount: vi.fn() };
    window.darFieldWidgets = { 'global.Widget': spec };
    expect(lookupFieldWidget('global.Widget')).toBe(spec);
  });

  it('module registry wins over the window global on conflict', () => {
    const moduleSpec = { mount: vi.fn() };
    const globalSpec = { mount: vi.fn() };
    window.darFieldWidgets = { 'shared.Widget': globalSpec };
    registerFieldWidget('shared.Widget', moduleSpec);
    expect(lookupFieldWidget('shared.Widget')).toBe(moduleSpec);
  });

  it('is robust when window.darFieldWidgets is undefined', () => {
    // Simulate a fresh page where no consumer has registered
    // anything via either path.
    delete window.darFieldWidgets;
    expect(lookupFieldWidget('anything')).toBeUndefined();
  });
});
