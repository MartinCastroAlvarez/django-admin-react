# SKILLS — Security & Compliance Lead

Concrete commands and patterns the role uses. A new session can
copy/paste from here.

## Read the security surface

```bash
# Where does the package gate access?
grep -rn 'has_permission\|has_view_permission\|has_add_permission\|has_change_permission\|has_delete_permission\|has_module_permission' django_admin_react/

# Anything bypassing the admin?
grep -rn 'objects\.all\|objects\.filter' django_admin_react/api/

# Anything csrf_exempt or auth-loose?
grep -rn 'csrf_exempt\|@login_required\|permission_classes' django_admin_react/

# Sensitive-field denylist usage?
grep -rn 'password\|secret\|token\|api_key\|apikey\|hash\|private_key' django_admin_react/api/serializers.py 2>/dev/null
```

## Run the local security pipeline

```bash
./scripts/lint.sh           # full pipeline (includes bandit + ruff S rules)
poetry run bandit -q -r django_admin_react
poetry run pip-audit
poetry run mypy django_admin_react
poetry run pytest tests/ -k "security or perm or csrf"
```

## Scan for committed secrets

```bash
# In a diff:
git diff --cached \
  | grep -iE '(ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|ghs_[A-Za-z0-9]{30,}|aws_secret_access_key|begin (rsa|ec|openssh) private)'

# In history (slow on big repos; install gitleaks if you can):
poetry run pip install gitleaks-detector 2>/dev/null || true
gitleaks detect --source . --no-banner 2>/dev/null || echo "(install gitleaks to run a full sweep)"
```

## Audit dependencies

```bash
# Python
poetry run pip-audit

# JS
cd frontend && pnpm audit --prod
```

## Test patterns for an endpoint

When reviewing a new endpoint:

```python
# tests/test_<endpoint>.py — required cases
def test_anonymous_rejected(client): ...
def test_non_staff_rejected(client, user): ...
def test_staff_without_perm_rejected(client, staff_user): ...
def test_staff_with_perm_ok(client, staff_user_with_perm): ...
def test_unregistered_model_404(client, staff_user): ...
def test_nonexistent_pk_404(client, staff_user): ...
def test_csrf_missing_on_unsafe_method_403(client, staff_user): ...
def test_readonly_field_not_writable(client, staff_user): ...
def test_excluded_field_not_writable(client, staff_user): ...
def test_sensitive_fields_not_serialized(client, staff_user): ...
def test_permissions_match_modeladmin(client, staff_user): ...
```

## Auth verification matrix

Two axes: `(user state) × (endpoint method)`. The default expected
response in each cell:

|                    | GET registry | GET list | GET detail | POST | PATCH | DELETE |
| ------------------ | :----------: | :------: | :--------: | :--: | :---: | :----: |
| Anonymous          | 403          | 403      | 403        | 403  | 403   | 403    |
| Non-staff          | 403          | 403      | 403        | 403  | 403   | 403    |
| Staff, no perm     | hides model | 403     | 403        | 403  | 403   | 403    |
| Staff, view only   | shows model | 200     | 200        | 403  | 403   | 403    |
| Staff, add+view    | shows model | 200     | 200        | 201  | 403   | 403    |
| Staff, change+view | shows model | 200     | 200        | 403  | 200   | 403    |
| Staff, delete+view | shows model | 200     | 200        | 403  | 403   | 204    |

CSRF missing on any unsafe method → 403 regardless of permission.

## Pre-commit hook (planned)

When `.pre-commit-config.yaml` lands:

```yaml
- repo: https://github.com/zricethezav/gitleaks
  rev: v8.x
  hooks:
    - id: gitleaks
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.x
  hooks:
    - id: ruff
    - id: ruff-format
- repo: https://github.com/PyCQA/bandit
  rev: 1.x
  hooks:
    - id: bandit
      args: ["-q", "-r", "django_admin_react"]
```

Plus a small local hook for the regex in `scripts/lint.sh`'s secret
section.

## Useful URLs (offline reference)

- OWASP ASVS — `https://owasp.org/www-project-application-security-verification-standard/`
- Django security docs — `https://docs.djangoproject.com/en/stable/topics/security/`
- pip-audit — `https://pypi.org/project/pip-audit/`
- Bandit — `https://bandit.readthedocs.io/`
- Gitleaks — `https://github.com/gitleaks/gitleaks`

(Don't `WebFetch` these autonomously; consult only when needed.)
