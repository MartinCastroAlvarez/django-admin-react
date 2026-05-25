# examples/library — Library demo app

Classic library catalog: authors, books, genres, members, and loans.
Demonstrates many-to-one relations with `PROTECT`/`SET_NULL` and a
one-to-one `User → Member` linkage.

## What's here

- `models.py` — `Genre`, `Author`, `Book`, `Member`, `Loan`.
- `admin.py` — `ModelAdmin` subclasses with `list_display`,
  `list_filter`, `search_fields`, `autocomplete_fields`, and one
  callable `list_display` (`Genre.book_count`).
- `tests/test_admin.py` — smoke test.

## Why this app demonstrates the design

- **PROTECT cascades**: `Book.author` is `PROTECT`. The React UI's
  delete confirmation must communicate when a delete is blocked by a
  protected FK. Currently the API surfaces Django's `ProtectedError`
  as a `409 conflict` (see `docs/api-contract.md` §6).
- **SET_NULL**: `Book.genre` is `SET_NULL` — deleting a `Genre`
  silently removes the link. The UI does not need to do anything
  special; the next list refresh shows `null`.
- **One-to-one**: `Member.user` is a `OneToOneField`. In v1 the React
  UI treats it as a normal FK (with a uniqueness validation that the
  admin form enforces).
- **Callable list_display**: `GenreAdmin.book_count` is a method
  decorated with `@admin.display` — the API serializes it via
  `str(value)` per the contract.

## Running

Same procedure as [`../fintech/README.md`](../fintech/README.md). The
shared project at `examples/project/` will install this app.
