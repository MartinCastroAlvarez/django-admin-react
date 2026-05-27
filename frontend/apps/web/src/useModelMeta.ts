// Resolve a model's human labels from the loaded registry — the SPA's
// metadata source of truth. Used for page headings + breadcrumbs so they
// show "Tenants" / "Tenant" (honouring Meta.verbose_name[_plural]) rather
// than the lowercase URL `model_name`. Matches by the routable
// real_app_label (falling back to the display app_label); returns the raw
// model_name for both labels when the model isn't found.
//
// Labels are capfirst'd for display: Django stores verbose_name lowercase
// by convention and capitalises the first letter at render time (the
// admin templates use `{{ ...|capfirst }}`), so a breadcrumb reads
// "Consolidated bank account evaluations", not the raw lowercase string.

import { useMemo } from 'react';

import { useRegistry } from '@dar/data';

export interface ModelMeta {
  singular: string;
  plural: string;
}

// Uppercase only the first character (Django's `capfirst`), leaving the
// rest untouched — never title-case, which would mangle proper nouns and
// acronyms inside a verbose_name.
function capfirst(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function useModelMeta(appLabel: string, modelName: string): ModelMeta {
  const registry = useRegistry();
  return useMemo(() => {
    for (const app of registry.data?.apps ?? []) {
      for (const m of app.models) {
        if (m.model_name === modelName && (m.real_app_label === appLabel || m.app_label === appLabel)) {
          return { singular: capfirst(m.verbose_name), plural: capfirst(m.verbose_name_plural) };
        }
      }
    }
    return { singular: capfirst(modelName), plural: capfirst(modelName) };
  }, [registry.data, appLabel, modelName]);
}
