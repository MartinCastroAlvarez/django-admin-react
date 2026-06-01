// ChangeForm — the form-spec-driven change form (#659).
//
// On edit, fetch the ModelAdmin-resolved form spec (rest-api 1.4.0+, #59)
// and render:
//   - the legacy admin in an iframe, when the admin overrides
//     `change_form_template` (`renderer: "legacy-iframe"`);
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
import { LegacyIframe } from './LegacyIframe';

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

  if (spec.renderer === 'legacy-iframe') {
    return <LegacyIframe url={spec.legacy_url} onCancel={onCancel} />;
  }

  return (
    <EditForm data={detailFromFormSpec(data, spec)} onCancel={onCancel} onSave={onSave} />
  );
}
