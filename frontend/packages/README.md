# frontend/packages/ — single-responsibility React packages

Each subfolder is its own pnpm package with a tight scope. Packages
depend on each other in this order (low → high):

```
@dar/ui                ← primitives, no business logic
@dar/api               ← REST client + React Query hooks
                         (only @dar/data may import this)
@dar/data              ← React Context + localStorage SWR + debounced
                         mutations; the single data source for UI
@dar/list, @dar/details, @dar/models
                       ← compose @dar/ui + @dar/data into pages
@dar/web             ← composes everything; builds with Vite
```

## The data layering rule

There is **one** data path inside the SPA, enforced by lint in PR #6:

```
@dar/api  ◄── network ──►  Django REST endpoints
   ▲
   │  (only @dar/data may import @dar/api)
   ▼
@dar/data  ◄── React Context ──►  @dar/list, @dar/details, @dar/models, @dar/web
```

UI packages (`list`, `details`, `models`, `shell`) **must not**
`import "@dar/api"` directly. See `ARCHITECTURE.md` §5.2a.

## Rules per package

| Package          | May depend on                                  | May NOT contain / import                                           |
| ---------------- | ---------------------------------------------- | ------------------------------------------------------------------ |
| `@dar/ui`        | React, Tailwind                                | API code, model names, business logic                              |
| `@dar/api`       | React, React Query, fetch                      | UI primitives, model names                                         |
| `@dar/data`      | React, `@dar/api`, localStorage                | UI primitives, model names                                         |
| `@dar/list`      | `@dar/ui`, `@dar/data`                         | `@dar/api`; model-specific names                                   |
| `@dar/details`   | `@dar/ui`, `@dar/data`                         | `@dar/api`; model-specific names                                   |
| `@dar/models`    | `@dar/ui`, `@dar/data`                         | `@dar/api`; model-specific names                                   |
| `@dar/web`     | `@dar/ui`, `@dar/data`, list/details/models + React Router | `@dar/api`; nothing model-specific                      |

Anything model-specific lives in `examples/` (consumer projects) or
`tests/test_project/`.
