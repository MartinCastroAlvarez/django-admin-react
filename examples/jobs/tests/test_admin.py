"""Backend tests for the Job custom-form fixture.

Exercises the legacy ``/admin/`` side of the contract — the side the React
SPA renders server-side as an html-fragment for Path B (#679). Pure Django
``TestCase`` + test client; no browser / e2e.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from examples.jobs.models import Job


class JobAdminRegistrationTests(TestCase):
    def test_job_registered(self) -> None:
        self.assertIn(Job, admin.site._registry)


class JobCustomViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_superuser(
            username="root",
            email="root@example.com",
            password="x",  # noqa: S106
        )
        cls.job = Job.objects.create(name="nightly", status="idle")

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def _change_url(self) -> str:
        return reverse("admin:jobs_job_change", args=[self.job.pk])

    def test_path_a_renders_stock_change_form(self) -> None:
        """No query → Django's stock change form (the metadata textarea)."""
        resp = self.client.get(self._change_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "vLargeTextField")
        self.assertNotContains(resp, 'id="run-custom-form"')

    def test_path_b_renders_custom_dual_listbox(self) -> None:
        """?run_custom=1 → the hand-rolled dual-listbox template."""
        resp = self.client.get(self._change_url() + "?run_custom=1")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "admin/jobs/job/run_custom.html")
        self.assertContains(resp, 'id="run-custom-form"')
        # Defaults pre-populate the "selected" column in default_order.
        self.assertContains(resp, 'data-step="fetch"')

    def test_path_b_post_preserves_order(self) -> None:
        """POST keeps the right column's order via getlist()."""
        resp = self.client.post(
            self._change_url() + "?run_custom=1",
            data={"selected_steps": ["validate", "fetch", "transform"]},
        )
        # Redirects back to the stock change page (Path A) on success.
        self.assertRedirects(resp, self._change_url())
        messages = list(resp.wsgi_request._messages)
        self.assertTrue(any("validate → fetch → transform" in str(m) for m in messages))

    def test_path_b_post_empty_is_rejected(self) -> None:
        resp = self.client.post(self._change_url() + "?run_custom=1", data={})
        # Redirects back to the same custom view with an error message.
        self.assertEqual(resp.status_code, 302)
        self.assertIn("run_custom=1", resp["Location"])


class JobHtmlFragmentApiTests(TestCase):
    """End-to-end exercise of the SPA's html-fragment path (#679) against the
    example backend's REST API — the side the React SPA actually consumes.

    The SPA fetches ``GET …/form-spec/?run_custom=1`` (→ ``html-fragment``)
    and POSTs the injected form back to ``POST …/<pk>/change/?run_custom=1``
    (→ another ``html-fragment`` on a validation error, or a ``redirect`` on
    success, with Django ``messages`` surfaced for SPA toasts). Pure Django
    ``TestCase`` + test client; no browser / e2e.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_superuser(
            username="root",
            email="root@example.com",
            password="x",  # noqa: S106
        )
        cls.job = Job.objects.create(name="nightly", status="idle")

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def _form_spec_url(self) -> str:
        return f"/admin-react/api/v1/jobs/job/{self.job.pk}/form-spec/?run_custom=1"

    def _change_post_url(self) -> str:
        return f"/admin-react/api/v1/jobs/job/{self.job.pk}/change/?run_custom=1"

    def test_form_spec_returns_html_fragment(self) -> None:
        """The custom-template view resolves to a server-rendered html-fragment
        (not the JSON form-spec, never an iframe)."""
        resp = self.client.get(self._form_spec_url())
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["renderer"], "html-fragment")
        # The dual-listbox markup + the inline JS survive into the fragment.
        self.assertIn('data-step="fetch"', payload["html"])
        self.assertIn("<script>", payload["html"])
        # The form wiring the SPA needs is present.
        self.assertTrue(payload["csrf_token"])
        self.assertEqual(payload["method"], "POST")
        self.assertIn("run_custom=1", payload["submit_url"])

    def test_post_empty_re_renders_fragment_with_error(self) -> None:
        """An empty selection re-renders the fragment (the PRG-to-self idiom)
        and carries the error message for the SPA to toast."""
        resp = self.client.post(self._change_post_url(), data={})
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["renderer"], "html-fragment")
        self.assertTrue(
            any(m["level"] == "error" for m in payload["messages"]),
            payload["messages"],
        )

    def test_post_selection_redirects_to_spa(self) -> None:
        """A valid selection redirects; the target is mapped onto the SPA prefix
        and the success message is carried for the SPA to toast."""
        resp = self.client.post(
            self._change_post_url(),
            data={"selected_steps": ["validate", "fetch"]},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["renderer"], "redirect")
        # Mapped onto the SPA prefix (not the legacy /admin/ mount).
        self.assertNotIn("/admin/", payload["to"])
        self.assertTrue(
            any("validate → fetch" in m["text"] for m in payload["messages"]),
            payload["messages"],
        )
