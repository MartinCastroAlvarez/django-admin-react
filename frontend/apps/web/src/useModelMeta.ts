// Resolve a model's human labels from the loaded registry — the SPA's
// metadata source of truth. Used for page headings + breadcrumbs so they
// show "Tenants" / "Tenant" (honouring Meta.verbose_name[_plural]) rather
// than the lowercase URL `model_name`. Matches by the routable
// real_app_label (falling back to the display app_label); returns the raw
// model_name for both labels when the model isn't found.

import { useMemo } from 'react';

import { useRegistry } from '@dar/data';

export interface ModelMeta {
  singular: string;
  plural: string;
}

export function useModelMeta(appLabel: string, modelName: string): ModelMeta {
  const registry = useRegistry();
  return useMemo(() => {
    for (const app of registry.data?.apps ?? []) {
      for (const m of app.models) {
        if (m.model_name === modelName && (m.real_app_label === appLabel || m.app_label === appLabel)) {
          return { singular: m.verbose_name, plural: m.verbose_name_plural };
        }
      }
    }
    return { singular: modelName, plural: modelName };
  }, [registry.data, appLabel, modelName]);
}
