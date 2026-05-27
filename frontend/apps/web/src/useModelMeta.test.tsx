import { describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';

import { useModelMeta } from './useModelMeta';

// Drive the hook from a controllable fake registry.
const registry = vi.hoisted(() => ({ data: null as unknown }));

vi.mock('@dar/data', () => ({
  useRegistry: () => registry,
}));

function setRegistry(models: Record<string, unknown>[]): void {
  registry.data = { apps: [{ app_label: 'bank', models }] };
}

describe('useModelMeta', () => {
  it('capfirsts the verbose names so breadcrumbs read "Consolidated …", not lowercase', () => {
    setRegistry([
      {
        model_name: 'evaluation',
        app_label: 'bank',
        real_app_label: 'bank',
        verbose_name: 'consolidated bank account evaluation',
        verbose_name_plural: 'consolidated bank account evaluations',
      },
    ]);
    const { result } = renderHook(() => useModelMeta('bank', 'evaluation'));
    expect(result.current.plural).toBe('Consolidated bank account evaluations');
    expect(result.current.singular).toBe('Consolidated bank account evaluation');
  });

  it('only touches the first character — acronyms/proper nouns mid-name survive', () => {
    setRegistry([
      {
        model_name: 'apikey',
        app_label: 'bank',
        real_app_label: 'bank',
        verbose_name: 'iOS API key',
        verbose_name_plural: 'iOS API keys',
      },
    ]);
    const { result } = renderHook(() => useModelMeta('bank', 'apikey'));
    // capfirst uppercases the first char only; the rest is verbatim
    // (title-casing would wreck "iOS"/"API").
    expect(result.current.plural).toBe('IOS API keys');
    expect(result.current.singular).toBe('IOS API key');
  });

  it('falls back to a capfirst model_name when the model is absent from the registry', () => {
    registry.data = { apps: [] };
    const { result } = renderHook(() => useModelMeta('ghost', 'widget'));
    expect(result.current.plural).toBe('Widget');
    expect(result.current.singular).toBe('Widget');
  });
});
