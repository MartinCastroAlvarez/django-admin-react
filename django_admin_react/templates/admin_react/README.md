# django_admin_react/templates/admin_react/

Django template directory for the SPA shell.

- `index.html` — the SPA entry point. Renders the React root element
  and exposes the mount point via a `<meta name="dar-mount" ...>` tag.

Only one HTML file lives here. All routing happens client-side via
React Router. The view that renders this template is
`django_admin_react.views.SpaIndexView` (PR #6).
