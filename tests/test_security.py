"""Central security regression tests.

This file is the home for the **cross-cutting** security tests every
PR must keep green. Endpoint-specific security cases continue to live
in ``tests/test_<endpoint>.py``, but anything that applies to the
whole package (code-level scans, response-header invariants, sensitive-
field denylist) lives here.

The mandatory per-endpoint matrix is in
``ACCEPTANCE.md`` §4.15. The acceptance criteria S-1 … S-66 are in
``ACCEPTANCE.md`` §4.

Conventions:

- Tests are split by ACCEPTANCE.md section, with the S-NN tag in the
  test name where one applies. Future agents reading a failure can
  jump straight to the criterion it covers.
- "Code-level" tests grep the package source — they catch regressions
  that the linters don't (e.g., someone adding ``csrf_exempt`` past
  the pre-commit hook).
- Endpoint-specific HTTP tests in this file are limited to invariants
  that apply uniformly across endpoints (e.g., 403 envelope shape).
  Endpoint behaviour is covered in the matching ``test_<endpoint>.py``.
"""

from __future__ import annotations

import ast
import re
import subprocess  # nosec B404 — used only on `git grep` against own repo
from pathlib import Path

import pytest
from django.test import Client

# Repo root resolved from this file's path (tests/test_security.py).
REPO_ROOT = Path(__file__).resolve().parent.parent
PKG_ROOT = REPO_ROOT / "django_admin_react"
API_ROOT = PKG_ROOT / "api"


# --------------------------------------------------------------------------- #
# §4.1 / §4.6 / §4.8 — code-level invariants                                  #
# These tests catch regressions where someone bypasses a security rule by    #
# editing source. They duplicate the pre-commit hook checks intentionally    #
# because not every contributor enables pre-commit locally.                  #
# --------------------------------------------------------------------------- #


def _files_under(root: Path, suffix: str = ".py") -> list[Path]:
    return [p for p in root.rglob(f"*{suffix}") if "__pycache__" not in p.parts]


def _grep(pattern: str, paths: list[Path]) -> list[tuple[Path, int, str]]:
    """Plain-text regex grep across files; returns (file, lineno, line)."""
    rx = re.compile(pattern)
    hits: list[tuple[Path, int, str]] = []
    for path in paths:
        try:
            with path.open(encoding="utf-8") as fh:
                for i, line in enumerate(fh, start=1):
                    if rx.search(line):
                        hits.append((path, i, line.rstrip()))
        except OSError:
            continue
    return hits


def test_s26_no_csrf_exempt_in_package() -> None:
    """S-26: ``@csrf_exempt`` must not appear anywhere under the package.

    Matches only the decorator usage (``@csrf_exempt`` at start of a
    line, possibly indented) and the import. Docstring mentions
    explaining why we do *not* use it are ignored — a substring match
    over-rejects.
    """
    rx = r"^\s*@csrf_exempt|from\s+django\.views\.decorators\.csrf\s+import\s+csrf_exempt"
    hits = _grep(rx, _files_under(PKG_ROOT))
    assert hits == [], f"@csrf_exempt found in package source: {hits}"


def _find_objects_all_or_filter(path: Path) -> list[int]:
    """Return line numbers of real ``<x>.objects.(all|filter)(...)`` calls.

    Uses AST so docstring and comment occurrences of the pattern are
    ignored.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    hits: list[int] = []
    for node in ast.walk(tree):
        # Look for Call(func=Attribute(attr in {all, filter},
        #                                value=Attribute(attr='objects', ...)))
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in {"all", "filter"}:
            continue
        inner = func.value
        if isinstance(inner, ast.Attribute) and inner.attr == "objects":
            hits.append(node.lineno)
    return hits


def test_s15_no_objects_all_or_filter_in_api() -> None:
    """S-15: ``Model.objects.all()`` / ``Model.objects.filter()`` must not
    appear in ``django_admin_react/api/``. The starting queryset is always
    ``ModelAdmin.get_queryset(request)``.

    AST-based so docstrings / comments that document the rule are ignored.
    """
    bad: list[tuple[Path, int]] = []
    for path in _files_under(API_ROOT):
        for lineno in _find_objects_all_or_filter(path):
            bad.append((path, lineno))
    assert bad == [], f"Model.objects.all|filter found in api/: {bad}"


def test_s10_no_user_has_perm_in_api() -> None:
    """S-10: never use ``user.has_perm(...)`` directly — always go through
    ``ModelAdmin.has_*_permission``.
    """
    hits = _grep(r"user\.has_perm\(", _files_under(API_ROOT))
    assert hits == [], f"user.has_perm() found in api/: {hits}"


def test_s12_no_client_string_imported_directly() -> None:
    """S-12: ``import_string``/``apps.get_model`` must only appear in the
    helpers that wrap a ``_registry`` lookup. We grep for the dangerous
    callsites and check they live inside ``registry.py`` (the gate).
    """
    hits = _grep(r"\b(import_string|apps\.get_model)\(", _files_under(API_ROOT))
    bad = [h for h in hits if h[0].name != "registry.py"]
    assert bad == [], f"Dangerous symbol lookup outside registry.py: {bad}"


def test_s13_no_admin_register_in_package() -> None:
    """S-13: the package never auto-registers a model. ``admin.site.register``
    and ``@admin.register`` are forbidden inside ``django_admin_react/``.
    """
    hits = _grep(r"(admin\.site\.register|@admin\.register)\b", _files_under(PKG_ROOT))
    assert hits == [], f"admin registration call found in package: {hits}"


def test_s52_no_default_cors_in_package() -> None:
    """S-52: the package never bundles a CORS middleware or sets
    ``Access-Control-Allow-Origin`` defaults.
    """
    hits = _grep(r"(Access-Control|django\.middleware\.cors|cors_headers)", _files_under(PKG_ROOT))
    # Exact `Access-Control` substring may appear only in test fixtures, which
    # are not under PKG_ROOT — so any hit here is a regression.
    assert hits == [], f"CORS-related code found in package: {hits}"


def test_s54_no_debug_or_introspection_endpoint() -> None:
    """S-54: no ``__debug__``-style endpoint in URL patterns or view names."""
    hits = _grep(r"__debug__|introspect_routes|inspect_routes", _files_under(PKG_ROOT))
    assert hits == [], f"Debug/introspection endpoint reference: {hits}"


def test_s5_no_parallel_auth_mechanism_in_views() -> None:
    """S-5 (revised): the package ships no parallel auth *mechanism*.

    History: the original S-5 forbade *any* login/password view by
    filename. The project has since deliberately shipped thin JSON entry
    points that **delegate** to Django's own auth — a React login/logout
    (``auth.py``, PRs #167/#168/#120) and an admin password-set shell
    (``password.py``, Issue #252). Those are UI shells over
    ``authenticate`` / ``login`` / ``logout`` / ``AdminPasswordChangeForm``
    / ``user.set_password``; they invent no credential machinery. The
    original filename check never actually caught ``auth.py`` (its stem is
    "auth"), so it was enforcing a loophole, not the invariant.

    The invariant that actually matters — and that this test enforces — is
    that no view implements its own auth *mechanism*. Forbidden in any
    view file:

    - **JWT / OAuth** of any kind (a parallel token/identity system).
    - **Credential minting / hashing done here** instead of delegating to
      Django: ``make_password``, ``set_unusable_password``,
      ``jwt.encode``, ``secrets.token_*``, ``create_access_token``,
      ``itsdangerous``. The only password path allowed is the delegation
      in ``password.py`` (``ModelAdmin.change_password_form`` →
      ``user.set_password`` via the admin's own form).

    See ``ACCEPTANCE.md`` §4 S-5 for the criterion text and the ADR in
    ``docs/agents/decisions.md`` recording the React-auth reconciliation.
    """
    views_dir = API_ROOT / "views"
    jwt_oauth_rx = re.compile(r"\b(jwt|oauth)\b", re.IGNORECASE)
    minting_rx = re.compile(
        r"\b(make_password|set_unusable_password|jwt\.encode|"
        r"secrets\.token_\w+|create_access_token|itsdangerous)\b"
    )
    offenders: list[str] = []
    for path in _files_under(views_dir):
        text = path.read_text(encoding="utf-8")
        if jwt_oauth_rx.search(text) or minting_rx.search(text):
            offenders.append(path.name)
    assert offenders == [], f"Parallel-auth mechanism found in views: {offenders}"


def test_s38_gitignore_blocks_secret_paths() -> None:
    """S-38: ``.gitignore`` blocks .env / *.pem / *.key / *.crt / secrets/."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    required = [".env", "*.pem", "*.key", "*.crt", "secrets/"]
    missing = [pat for pat in required if pat not in gitignore]
    assert missing == [], f".gitignore is missing patterns: {missing}"


def test_s37_no_committed_token_patterns_in_head() -> None:
    """S-37: HEAD must not contain any obvious token / private-key pattern.

    Uses ``git grep`` (faster than scanning the working tree) and skips
    this file's own regex literals via a structural filter.
    """
    # `git grep -nE` against HEAD. We skip our own test file (which contains
    # the regex by design). Absolute-path `git` resolved from PATH lookup
    # at import time to keep bandit happy.
    git_bin = "/usr/bin/git" if Path("/usr/bin/git").exists() else "git"
    args = [
        git_bin,
        "-C",
        str(REPO_ROOT),
        "grep",
        "-nIE",
        "--",
        r"ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|ghs_[A-Za-z0-9]{30,}|"
        + r"github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|"
        + r"BEGIN (RSA|EC|OPENSSH) PRIVATE",
    ]
    result = subprocess.run(  # noqa: S603
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    # Filter out the lines that come from documenting these patterns:
    # tests/test_security.py (this file), scripts/lint.sh, .pre-commit-config.yaml,
    # docs/agents — anywhere a security-policy file references the regex
    # itself. `docs/agents/` covers the per-role subfolders too.
    DOC_PATHS = (
        "tests/test_security.py",
        "scripts/lint.sh",
        "scripts/audit-deps.sh",
        ".pre-commit-config.yaml",
        "docs/agents/",
        "docs/threat-model.md",
        "ACCEPTANCE.md",
        "SECURITY.md",
    )
    lines = [
        ln
        for ln in (result.stdout or "").splitlines()
        if ln and not any(ln.startswith(p) for p in DOC_PATHS)
    ]
    if lines:
        joined = "\n".join(lines)
        raise AssertionError(f"Possible secret pattern in HEAD (filtered for doc refs):\n{joined}")


# --------------------------------------------------------------------------- #
# §4.6 S-30 — response headers on 403                                         #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_s30_forbidden_response_has_no_store(user_client: Client) -> None:
    """S-30: permission-denied responses set ``Cache-Control: no-store``."""
    response = user_client.get("/admin-react/api/v1/registry/")
    assert response.status_code == 403
    assert (
        response.headers.get("Cache-Control") == "no-store"
    ), f"Cache-Control was {response.headers.get('Cache-Control')!r}, expected 'no-store'"


@pytest.mark.django_db
def test_s30_registry_200_has_no_store(superuser_client: Client) -> None:
    """S-30 extended: 200 responses must also set ``Cache-Control:
    no-store``. Without it, an intermediate proxy or browser cache
    could serve User A's registry payload to User B (different
    permissions → cross-user data leak).
    """
    response = superuser_client.get("/admin-react/api/v1/registry/")
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"


@pytest.mark.django_db
def test_s30_list_200_has_no_store(superuser_client: Client) -> None:
    """S-30 extended for the list endpoint."""
    response = superuser_client.get("/admin-react/api/v1/auth/user/")
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"


@pytest.mark.django_db
def test_s30_detail_200_has_no_store(superuser_client: Client) -> None:
    """S-30 extended for the detail endpoint."""
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.first()
    assert user is not None, "superuser_client fixture should have created a user"
    response = superuser_client.get(f"/admin-react/api/v1/auth/user/{user.pk}/")
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"


# --------------------------------------------------------------------------- #
# §4.11 S-51 — HTTP method allow-list                                         #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "POST", "TRACE"])
@pytest.mark.django_db
def test_s51_registry_rejects_unsafe_methods(staff_client: Client, method: str) -> None:
    """S-51 (registry slice): the registry endpoint is GET-only.

    Any unsafe method returns 405 (Django's default for unsupported
    methods); body is empty or a Django default — important: never a
    stack trace, never an admin-data leak.
    """
    response = staff_client.generic(method, "/admin-react/api/v1/registry/")
    # Django's `View.http_method_names = ["get"]` enforces this.
    assert response.status_code in (
        405,
        403,
    ), f"{method} returned {response.status_code}, expected 405 (or 403 if CSRF rejects first)"
    # No body leakage even for 405 (Django returns the allow list, which is
    # acceptable — but no model / field / app data).
    body = response.content.decode("utf-8", errors="replace").lower()
    forbidden_in_body = ("password", "secret", "token", "api_key", "private_key")
    leaked = [k for k in forbidden_in_body if k in body]
    assert leaked == [], f"Sensitive substrings leaked in {method} response: {leaked}"


# --------------------------------------------------------------------------- #
# §4.1 S-1 — anonymous response body has zero leakage                         #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_s1_anonymous_body_has_no_model_or_field_leak(anon_client: Client) -> None:
    """S-1: anonymous response to the registry endpoint must not include
    any model name, field name, or username.
    """
    response = anon_client.get("/admin-react/api/v1/registry/")
    # 302 (login redirect) or 403 are both contract-compliant; the body
    # is only allowed to contain a generic message.
    assert response.status_code in (302, 403)
    body = response.content.decode("utf-8", errors="replace").lower()
    # The word "user" can appear in a generic message — that's fine — but
    # only if it isn't part of an admin-data structure. We check by JSON
    # shape: a forbidden envelope is exactly `{"error": {...}}`.
    if response.status_code == 403:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        canonical = {
            "error": {
                "code": "forbidden",
                "message": "You do not have permission.",
            }
        }
        assert (
            payload == canonical
        ), f"403 body is not the canonical forbidden envelope: {payload!r}"
    else:
        # 302 redirect — body should be near-empty.
        assert len(response.content) < 1024, "302 body is unexpectedly large; check for leakage"
        assert "password" not in body
        assert "api_key" not in body


# --------------------------------------------------------------------------- #
# §4.7 — sensitive-field denylist (scaffold; runs once the serializer lands)  #
# --------------------------------------------------------------------------- #


REQUIRED_SENSITIVE_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "hash",
    "private_key",
    "session",
    "nonce",
    "salt",
)


def test_s31_denylist_constant_exists_and_complete() -> None:
    """S-31: the serializer module exposes a
    ``SENSITIVE_NAME_SUBSTRINGS`` constant containing every required
    substring. Case-insensitive matching is enforced by the helper,
    not by this constant — the constant just lists the substrings.
    """
    from django_admin_react.api import serializers

    constant = serializers.SENSITIVE_NAME_SUBSTRINGS
    missing = [p for p in REQUIRED_SENSITIVE_SUBSTRINGS if p not in constant]
    assert missing == [], f"Denylist is missing required substrings: {missing}"


def test_s31_is_sensitive_field_name_matches_required_patterns() -> None:
    """S-31 (functional): every required substring is matched by
    ``is_sensitive_field_name`` — case-insensitive, substring match.
    """
    from django_admin_react.api.serializers import is_sensitive_field_name

    for pattern in REQUIRED_SENSITIVE_SUBSTRINGS:
        if not is_sensitive_field_name(pattern):
            raise AssertionError(f"plain match failed: {pattern!r}")
        # Substring + case-insensitive: a real field name like
        # ``user_password_hash`` must trip the denylist.
        if not is_sensitive_field_name(f"user_{pattern.upper()}_field"):
            raise AssertionError(f"substring/case match failed: {pattern!r}")
