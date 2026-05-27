# Extension contract

Three places a consumer can extend the SPA without forking it:

1. **Backend type vocabulary** — register a custom Django field type
   so the SPA knows how to serialize it. Already shipped via
   [`register_field_type`](../django_admin_react/api/serializers.py).
2. **Backend panel endpoints** — attach a per-model JSON endpoint
   under `…/<pk>/panel/<name>/` that returns data only your custom
   SPA component needs (audit trail, related records, status
   probes). Specified below; opt-in via the
   `PanelEndpointsMixin` on the consumer's `ModelAdmin`.
3. **Frontend extension points** — register a React widget /
   sidebar panel / list-toolbar action keyed by app / model
   (and optionally field). Specified below.

The point of the contract is that **`ModelAdmin` stays the only
source of truth**: a consumer extension layers on top of the
metadata-driven SPA, it doesn't replace it.

> **Implementation status (read before you build, #436).** Not all three
> points are wired end-to-end yet — this doc specifies the *contract*, and
> some of it is still aspirational:
>
> | Extension point | Status |
> | --- | --- |
> | 1. `register_field_type` (backend) | **Shipped** — usable today. |
> | 2. Panel endpoints (`…/<pk>/panel/<name>/`, backend) | **Backend shipped** — the endpoint serves data, but **the SPA does not render panels yet**, so a registered panel is not visible in the UI. |
> | 3. `registerFieldWidget` / `registerModelPanel` / `registerModelAction` (frontend) | **Not yet implemented** — the `@django-admin-react/extensions` package and these functions **do not exist yet**. The shape below is a draft for design feedback only; importing it will fail. |
>
> Tracking: [#436](https://github.com/MartinCastroAlvarez/django-admin-react/issues/436).
> Don't rely on §2's UI rendering or §3 for a production integration until
> this banner says otherwise.

---

## 1. Backend: `register_field_type` (already shipped)

See [`docs/api-contract.md`](api-contract.md) §4.1.

```python
# yourapp/apps.py
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    def ready(self):
        from django_admin_react.api.serializers import register_field_type
        from .fields import MoneyField

        register_field_type(
            "MoneyField",
            "decimal",
            serializer=lambda v: None if v is None else str(v.amount),
        )
```

Builtin types in the closed vocabulary cannot be overridden.

---

## 2. Backend: per-model panel endpoints

> **Status: backend shipped; SPA rendering not wired yet (#436).** The
> endpoint below serves panel data today, but no SPA component fetches
> `…/panel/<name>/` yet — so a registered panel is not visible in the UI
> until the frontend half lands. You can build + test the endpoint now;
> just don't expect it on screen.

Some custom UIs need data the standard detail endpoint doesn't
return: an audit trail, related-records mini-grid, derived stats,
external-service status probes. Without an extension point each
consumer would have to bolt this onto their own DRF surface, then
wire the SPA to talk to two backends.

Contract:

```python
# yourapp/admin.py
from django.contrib import admin
from django.http import JsonResponse

from django_admin_react.api.panels import PanelEndpointsMixin

@admin.register(Invoice)
class InvoiceAdmin(PanelEndpointsMixin, admin.ModelAdmin):
    panels = {
        "audit_trail": "get_audit_trail",
        "external_status": "get_external_status",
    }

    def get_audit_trail(self, request, obj):
        return {
            "entries": [
                {"at": str(entry.created_at),
                 "by": str(entry.user),
                 "what": entry.change}
                for entry in obj.audit_entries.all().order_by("-created_at")[:50]
            ]
        }

    def get_external_status(self, request, obj):
        return {"upstream": "ok", "checked_at": "2025-10-05T12:00:00Z"}
```

URL shape: `GET /admin-react/api/v1/<app>/<model>/<pk>/panel/<name>/`

Rules:

- Same auth gate as every other read endpoint (staff + AdminSite +
  `has_view_permission(request, obj)`).
- Panel name is re-resolved through `model_admin.panels` — never
  trusts the URL segment as a method lookup.
- Panel handler returns any JSON-serialisable value; the wire shape
  is opaque to the package (it's your panel, your shape).
- `Cache-Control: no-store` on every response.
- Unknown panel name → 404.
- A `ModelAdmin` without `PanelEndpointsMixin` returns 404 on every
  `…/panel/<name>/` URL (opt-in surface).

The mixin is intentionally minimal — the consumer's handler does
its own data shaping and validation. The package only enforces the
auth + name-resolution gate.

---

## 3. Frontend: `registerFieldWidget` / `registerModelPanel` /
   `registerModelAction`

> **Status: NOT YET IMPLEMENTED — contract drafted only (#436).** The
> `@django-admin-react/extensions` package and the `registerFieldWidget` /
> `registerModelPanel` / `registerModelAction` functions **do not exist
> yet**; the imports below will fail. This section documents the intended
> shape so consumers can design their custom widgets and give feedback —
> it is not a working API. Implementation lands with the SPA extension
> work; until then, treat everything in §3 as a proposal.

The frontend exposes three extension points. All registrations
happen at module load time (typically in your SPA bundle's entry).

### 3.1 `registerFieldWidget`

Replace the default widget for one field of one model.

```ts
import { registerFieldWidget } from "@django-admin-react/extensions";
import { MyInvoiceLineItemsEditor } from "./widgets/InvoiceLineItems";

registerFieldWidget({
  appLabel: "billing",
  modelName: "invoice",
  fieldName: "line_items",
  Component: MyInvoiceLineItemsEditor,
});
```

The component receives `{value, onChange, descriptor, disabled,
required, errors}` and is rendered inside the standard form layout.
Changes flow through the same dirty-tracking + auto-save the
built-in widgets use.

### 3.2 `registerModelPanel`

Inject a side panel on the detail view of one model.

```ts
import { registerModelPanel } from "@django-admin-react/extensions";
import { AuditTrailPanel } from "./panels/AuditTrail";

registerModelPanel({
  appLabel: "billing",
  modelName: "invoice",
  slot: "detail.sidebar",   // "detail.sidebar" | "detail.footer"
  Component: AuditTrailPanel,
});
```

The component receives `{obj, fetchPanel}`. `fetchPanel(name)`
hits the backend `…/panel/<name>/` endpoint described in §2,
caches the result per object, and re-fetches on object save.

### 3.3 `registerModelAction`

Add a per-row or per-list custom action button. Distinct from
`ModelAdmin.actions` (which runs server-side); use this for
client-only actions like "Open in Stripe dashboard".

```ts
import { registerModelAction } from "@django-admin-react/extensions";

registerModelAction({
  appLabel: "billing",
  modelName: "invoice",
  scope: "row",   // "row" | "list" | "detail"
  label: "Open in Stripe",
  icon: "external-link",
  onClick: (obj) => window.open(`https://dashboard.stripe.com/...${obj.pk}`),
});
```

### Three slots, then stop

The contract intentionally provides only three slots
(`field.widget`, `detail.{sidebar,footer}`, `<row|list|detail>
action`). Anything more would defeat the metadata-driven
property: consumers would be encouraged to build per-model React
pages, which is just "fork the SPA in a friendlier directory".

If you find yourself wanting a fourth slot, the right path is
usually to push the customisation into a `ModelAdmin` override
that surfaces through the existing API (a `@admin.display`
column, a `SimpleListFilter`, a `ModelAdmin.action`, a custom
field type via `register_field_type`).

---

## 4. What does NOT count as an extension point

- **Per-model React pages.** Forking the SPA in a friendlier
  package boundary. Reject.
- **Theme overrides.** Tailwind theming via CSS variables is the
  documented approach (see [`docs/ux/principles.md`](ux/principles.md)).
- **Replacing the auth flow.** The package reuses Django sessions;
  swap out the consumer's auth backend, not the SPA's gate.
- **Changing the wire contract.** Add an issue first; the contract
  is documented in [`docs/api-contract.md`](api-contract.md) and
  changes are tier-5 per
  [`docs/agents/autonomy-policy.md`](agents/autonomy-policy.md).

---

## 5. References

- Backend type registration: [`django_admin_react/api/serializers.py::register_field_type`](../django_admin_react/api/serializers.py)
- Backend panel mixin: [`django_admin_react/api/panels.py`](../django_admin_react/api/panels.py)
- Wire contract: [`docs/api-contract.md`](api-contract.md)
- Architectural rationale: [`ARCHITECTURE.md`](../ARCHITECTURE.md) §5 (extensibility principles)
