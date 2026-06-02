// ChangeForm — the form-spec-driven change form (#659, #679).
//
// On edit, fetch the ModelAdmin-resolved form spec (rest-api 1.4.0+, #59)
// and render:
//   - a server-rendered html-fragment INSIDE the SPA shell, when the admin
//     overrides `change_form_template` (`renderer: "html-fragment"`,
//     rest-api 1.7.0+, #679) — no iframe;
//   - otherwise the existing EditForm, with its fields + fieldsets sourced
//     from the spec (request-aware get_form / fieldsets / readonly, the
//     closed widget.kind enum) instead of being discovered client-side
//     from the model serializer.
//
// If the spec can't be fetched (an older backend without the endpoint, a
// transient error), we fall back to the detail-payload-driven EditForm so
// editing still works — graceful degradation, never a broken page.

import {
  type DetailResponse,
  useApiClient,
  useFormSpec,
} from '@dar/data';

import { RecordSkeleton } from '../../components/RecordSkeleton';
import { detailFromFormSpec } from './adaptFormSpec';
import { EditForm, type SaveAction } from './EditForm';
import { HtmlFragment } from './HtmlFragment';

export interface ChangeFormProps {
  data: DetailResponse;
  appLabel: string;
  modelName: string;
  pk: string;
  /** Original change-form querystring (forwarded for request-aware get_form). */
  query?: string;
  onCancel: () => void;
  onSave: (payload: import('@dar/data').UpdatePayload, action: SaveAction) => Promise<void>;
}

export function ChangeForm({
  data,
  appLabel,
  modelName,
  pk,
  query,
  onCancel,
  onSave,
}: ChangeFormProps) {
  const client = useApiClient();
  const { data: spec, loading, error } = useFormSpec({
    client,
    appLabel,
    modelName,
    pk,
    // `query` is always a string from the caller (URLSearchParams.toString());
    // default to '' so the optional prop is never assigned `undefined`
    // (exactOptionalPropertyTypes).
    query: query ?? '',
  });

  // First load with nothing cached → skeleton. (Background refresh is off
  // for the spec, so this only shows on the very first edit-mode entry.)
  if (loading && !spec) return <RecordSkeleton />;

  // Spec unavailable (older backend / transient error) → fall back to the
  // detail-driven form so the operator can still edit.
  if (error && !spec) {
    return <EditForm data={data} onCancel={onCancel} onSave={onSave} />;
  }
  if (!spec) return <EditForm data={data} onCancel={onCancel} onSave={onSave} />;

  if (spec.renderer === 'html-fragment') {
    // Custom `change_form_template` (#679): inject the server-rendered form
    // in-shell. `onCancel` is unused here — the fragment owns its own
    // submit/cancel affordances and redirects via SPA navigate.
    return (
      <HtmlFragment
        fragment={spec}
        appLabel={appLabel}
        modelName={modelName}
        pk={pk}
        query={query ?? ''}
      />
    );
  }

  return (
    <EditForm data={detailFromFormSpec(data, spec)} onCancel={onCancel} onSave={onSave} />
  );
}
