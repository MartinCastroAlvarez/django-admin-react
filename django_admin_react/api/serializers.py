"""Conservative field serialization.

Native types: str, int, float, bool, None, Decimal (as string), UUID
(as string), date / datetime (ISO 8601). ForeignKey → {id, label}.
ManyToMany → type=unsupported in v1. Unknown values fall back to
str(value) rather than crashing.

A denylist of sensitive-shaped field names (password, secret, token,
api_key, hash, ...) is applied on top of the admin form's exclusion
rules. See `SECURITY.md` §2.7 and `docs/api-contract.md` §4.

Implementation lands in PR #4.
"""
