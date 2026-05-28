// FieldValueView — render one wire-shape field/cell value.
//
// Plain values go through `renderValue` (escaped text). The backend's
// safe-HTML envelope (`{ html }`, emitted only for `SafeString` /
// `format_html` `list_display` + readonly display methods) is rendered
// as markup via `dangerouslySetInnerHTML` — matching Django's own
// changelist. A plain string is never the html envelope, so untrusted
// text (e.g. a `CharField` holding `<script>`) stays inert. The trust
// boundary is identical to Django's `mark_safe`. See SECURITY.md + #172.

import { Suspense, lazy } from 'react';
import { Check, X } from 'lucide-react';
import { Link } from 'react-router-dom';

import {
  isFileValue,
  isForeignKeyValue,
  isHtmlValue,
  renderValue,
  type FieldType,
  type FieldValue,
} from '@dar/data';

// Lazy-loaded so detail pages whose models hold no large JSON-shaped
// strings pay zero bundle weight for the viewer (#576). Vite splits the
// import boundary into its own chunk; the fallback below is the same
// monospace block we render below the threshold, so the transition is
// imperceptible when the chunk arrives.
const JsonViewer = lazy(() => import('./JsonViewer'));

// Threshold below which we don't bother with the viewer — a small JSON
// blob renders fine as plain text and any chrome is overkill (#576).
// 1 KB is the issue-acceptance threshold.
const JSON_VIEWER_THRESHOLD = 1024;

// Cheap detection: a string field whose trimmed value starts with `{`
// or `[` AND parses as JSON. We only call `JSON.parse` after the
// length + bracket-shape gate to keep the read path cheap for every
// detail-page render.
function tryParseLargeJson(value: unknown): { raw: string; parsed: unknown } | null {
  if (typeof value !== 'string') return null;
  if (value.length < JSON_VIEWER_THRESHOLD) return null;
  const trimmed = value.trimStart();
  if (trimmed.length === 0) return null;
  const first = trimmed[0];
  if (first !== '{' && first !== '[') return null;
  try {
    const parsed = JSON.parse(value) as unknown;
    return { raw: value, parsed };
  } catch {
    return null;
  }
}

interface FieldValueViewProps {
  value: FieldValue | undefined;
  /** The field's wire type — when `datetime`/`date`/`time`, the value is
   *  rendered as a localized display string instead of raw ISO (#413).
   *  Explicitly allows `undefined` so callers can forward a possibly-absent
   *  column/field type under `exactOptionalPropertyTypes`. */
  type?: FieldType | undefined;
}

export function FieldValueView({ value, type }: FieldValueViewProps) {
  // BooleanField / @admin.display(boolean=True): render Django's
  // green-check / red-X icon instead of "Yes"/"No" text. A null boolean is
  // indistinguishable from any other null here, so it falls through to the
  // em-dash placeholder (matching Django's "-" for an unknown boolean).
  if (typeof value === 'boolean') {
    return value ? (
      <Check className="inline-block h-4 w-4 text-green-600" role="img" aria-label="Yes" />
    ) : (
      <X className="inline-block h-4 w-4 text-red-600" role="img" aria-label="No" />
    );
  }
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
          className="font-medium text-primary hover:underline"
        >
          {value.label}
        </Link>
      );
    }
    return <span className="font-medium text-gray-700">{value.label}</span>;
  }
  // JSON-shaped string fields (#576): a TextField / JSONField whose
  // string value parses as JSON and exceeds the threshold renders
  // through the syntax-highlighted, collapsible viewer with a
  // copy-the-original-string button. Below the threshold, or for
  // non-JSON strings, fall through to the plain `renderValue` path
  // — small snippets are fine as monospace text and any chrome would
  // be overkill (CLAUDE.md §7, no redundant chrome). The viewer is
  // lazy-loaded so detail pages without JSON fields pay nothing.
  const json = tryParseLargeJson(value);
  if (json) {
    return (
      <Suspense fallback={<pre className="whitespace-pre-wrap font-mono text-xs">{json.raw}</pre>}>
        <JsonViewer raw={json.raw} parsed={json.parsed} />
      </Suspense>
    );
  }
  // FileField / ImageField: a download link to the stored file (matching
  // Django admin's "Currently: <a>" affordance). No URL → plain name.
  if (isFileValue(value)) {
    if (!value.url) return <span className="text-gray-500">{value.name}</span>;
    return (
      <a
        href={value.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary hover:underline"
      >
        {value.name}
      </a>
    );
  }
  return <>{renderValue(value, type)}</>;
}
