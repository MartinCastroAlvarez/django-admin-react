// FieldValueView — render one wire-shape field/cell value.
//
// Plain values go through `renderValue` (escaped text). The backend's
// safe-HTML envelope (`{ html }`, emitted only for `SafeString` /
// `format_html` `list_display` + readonly display methods) is rendered
// as markup via `dangerouslySetInnerHTML` — matching Django's own
// changelist. A plain string is never the html envelope, so untrusted
// text (e.g. a `CharField` holding `<script>`) stays inert. The trust
// boundary is identical to Django's `mark_safe`. See SECURITY.md + #172.

import { Link } from 'react-router-dom';

import { isForeignKeyValue, isHtmlValue, renderValue, type FieldValue } from '@dar/data';

interface FieldValueViewProps {
  value: FieldValue | undefined;
}

export function FieldValueView({ value }: FieldValueViewProps) {
  if (isHtmlValue(value)) {
    return <span dangerouslySetInnerHTML={{ __html: value.html }} />;
  }
  // ForeignKey cells (#184): when the related model is admin-registered
  // the value carries `to`, so render a real navigable link to the
  // related object's detail page — matching Django admin's list_display
  // FK columns. `stopPropagation` keeps the click from also triggering
  // the surrounding row's onClick (which would open *this* row instead
  // of the related object). When `to` is absent (unregistered related
  // model) the label stays plain styled text — never a 404-bound link.
  if (isForeignKeyValue(value)) {
    if (value.to) {
      return (
        <Link
          to={`/${value.to.app_label}/${value.to.model_name}/${value.id}`}
          onClick={(e) => e.stopPropagation()}
          className="font-medium text-indigo-600 hover:underline"
        >
          {value.label}
        </Link>
      );
    }
    return <span className="font-medium text-gray-700">{value.label}</span>;
  }
  return <>{renderValue(value)}</>;
}
