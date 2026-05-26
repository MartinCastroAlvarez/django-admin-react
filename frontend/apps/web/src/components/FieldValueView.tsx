// FieldValueView — render one wire-shape field/cell value.
//
// Plain values go through `renderValue` (escaped text). The backend's
// safe-HTML envelope (`{ html }`, emitted only for `SafeString` /
// `format_html` `list_display` + readonly display methods) is rendered
// as markup via `dangerouslySetInnerHTML` — matching Django's own
// changelist. A plain string is never the html envelope, so untrusted
// text (e.g. a `CharField` holding `<script>`) stays inert. The trust
// boundary is identical to Django's `mark_safe`. See SECURITY.md + #172.

import { isForeignKeyValue, isHtmlValue, renderValue, type FieldValue } from '@dar/data';

interface FieldValueViewProps {
  value: FieldValue | undefined;
}

export function FieldValueView({ value }: FieldValueViewProps) {
  if (isHtmlValue(value)) {
    return <span dangerouslySetInnerHTML={{ __html: value.html }} />;
  }
  // ForeignKey cells read as links (the related object's str()). Style
  // them as links so they're visually navigable — matches Django
  // admin's list_display FK columns. Full navigation to the related
  // detail needs the column's FK-target metadata (tracked in #184);
  // until then the row click (→ this row's detail) is the action.
  if (isForeignKeyValue(value)) {
    return <span className="text-blue-600 underline decoration-dotted">{value.label}</span>;
  }
  return <>{renderValue(value)}</>;
}
