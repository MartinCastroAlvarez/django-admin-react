import { Link } from 'react-router-dom';

import { type FieldDescriptor } from '@dar/data';
import { FieldValueView } from '@dar/details';

/**
 * Render a detail field's value. ForeignKey values become a navigable
 * link to the related object's detail page (#184 — Django-admin
 * parity), using the descriptor's `to` (the FK target's real
 * app_label + model_name) so the URL round-trips through resolve_model.
 * Everything else defers to FieldValueView.
 */
export function DetailValue({ field }: { field: FieldDescriptor }) {
  const v = field.value;
  if (
    field.type === 'foreignkey' &&
    field.to &&
    v &&
    typeof v === 'object' &&
    !Array.isArray(v) &&
    'id' in v
  ) {
    const fk = v as { id: number | string; label: string };
    return (
      <Link
        to={`/${field.to.app_label}/${field.to.model_name}/${fk.id}`}
        className="text-primary hover:underline"
      >
        {fk.label}
      </Link>
    );
  }
  // Choice field: show the human label for the stored value (Django's
  // get_FOO_display parity). The editor still submits the raw value via
  // `field.value`; this only changes the read-mode rendering. Scalar
  // values only — FK / file / html envelopes are objects handled above
  // or by FieldValueView.
  if (field.choices && field.choices.length > 0 && v !== null && typeof v !== 'object') {
    const match = field.choices.find((o) => String(o.value) === String(v));
    if (match) return <>{match.label}</>;
  }
  return <FieldValueView value={field.value} type={field.type} />;
}
