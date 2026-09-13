import importlib.util
import os
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.db.utils import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import ContactMessage, NewsletterSubscriber
from .views import CONTACT_MAX_PER_IP_PER_HOUR


def settings_module_path():
    return Path(settings.BASE_DIR) / "config" / "settings.py"


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class ContactFormAbuseTests(TestCase):
    """Each accepted submission sends two emails, one to a user-supplied address.
    Unthrottled, the form is an open mail relay; the resulting domain
    blacklisting would also stop OTP delivery and disable authentication."""

    def setUp(self):
        cache.clear()
        self.url = reverse("core:contact")
        self.payload = {
            "name": "Reader",
            "email": "reader@example.com",
            "phone": "9999999999",
            "subject": "Question",
            "message": "Hello, I have a question.",
            "website": "",
        }

    def tearDown(self):
        cache.clear()

    def _submit(self, **overrides):
        return self.client.post(self.url, {**self.payload, **overrides})

    def test_valid_submission_is_saved_and_emailed(self):
        response = self._submit()
        self.assertRedirects(response, self.url)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_honeypot_blocks_bot_submission(self):
        response = self._submit(website="http://spam.example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_cooldown_blocks_immediate_resubmission(self):
        self._submit()
        mail.outbox.clear()
        response = self._submit(email="other@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_per_ip_hourly_limit_is_enforced(self):
        # Distinct emails and a cleared cooldown isolate the per-IP rule.
        for index in range(CONTACT_MAX_PER_IP_PER_HOUR):
            self._submit(email=f"sender{index}@example.com")
            cache.delete("contact:cooldown:127.0.0.1")
        accepted = ContactMessage.objects.count()
        self.assertEqual(accepted, CONTACT_MAX_PER_IP_PER_HOUR)

        mail.outbox.clear()
        response = self._submit(email="overflow@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), accepted)
        self.assertEqual(len(mail.outbox), 0)

    def test_throttle_uses_rightmost_forwarded_for(self):
        # The leftmost X-Forwarded-For value is client-supplied and spoofable,
        # so rotating it must not grant extra quota.
        self._submit(email="a@example.com")
        response = self.client.post(
            self.url,
            {**self.payload, "email": "b@example.com"},
            HTTP_X_FORWARDED_FOR="1.2.3.4, 127.0.0.1",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 1)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class NewsletterRedirectTests(TestCase):
    """Referer is attacker-influenceable: a page on another origin can submit
    here, and blindly redirecting to the header made this an open redirect."""

    def setUp(self):
        self.url = reverse("core:newsletter")
        self.payload = {"email": "reader@example.com", "name": "Reader"}

    def test_external_referer_is_not_followed(self):
        response = self.client.post(self.url, self.payload, HTTP_REFERER="https://evil.example.com/phish")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil.example.com", response["Location"])
        self.assertEqual(response["Location"], reverse("home"))

    def test_protocol_relative_referer_is_not_followed(self):
        response = self.client.post(self.url, self.payload, HTTP_REFERER="//evil.example.com/phish")
        self.assertEqual(response["Location"], reverse("home"))

    def test_internal_referer_is_preserved(self):
        response = self.client.post(self.url, self.payload, HTTP_REFERER="http://testserver/latest/")
        self.assertEqual(response["Location"], "http://testserver/latest/")

    def test_relative_referer_is_preserved(self):
        response = self.client.post(self.url, self.payload, HTTP_REFERER="/trending/")
        self.assertEqual(response["Location"], "/trending/")

    def test_missing_referer_falls_back_home(self):
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response["Location"], reverse("home"))

    def test_malformed_referer_falls_back_home(self):
        response = self.client.post(self.url, self.payload, HTTP_REFERER="http://[::1")
        self.assertEqual(response["Location"], reverse("home"))

    def test_subscription_is_still_saved(self):
        self.client.post(self.url, self.payload, HTTP_REFERER="/trending/")
        self.assertTrue(NewsletterSubscriber.objects.filter(email="reader@example.com").exists())

    def test_duplicate_subscription_is_not_reported_as_a_bad_email(self):
        """The unique constraint makes a repeat signup fail validation, and the
        view used to respond "please enter a correct email" — wrong and
        confusing for someone who is simply already subscribed."""
        self.client.post(self.url, self.payload)
        response = self.client.post(self.url, self.payload, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("पहले से सब्सक्राइब" in m for m in messages), messages)
        self.assertFalse(any("सही ईमेल" in m for m in messages), messages)
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)

    def test_invalid_email_still_reports_an_error(self):
        response = self.client.post(self.url, {"email": "not-an-email", "name": ""}, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("सही ईमेल" in m for m in messages), messages)
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class HealthCheckTests(TestCase):
    def test_healthz_returns_ok(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["checks"]["database"], "ok")

    def test_healthz_is_not_cached(self):
        response = self.client.get("/healthz")
        self.assertIn("no-cache", response["Cache-Control"])

    def test_healthz_reports_503_when_database_is_down(self):
        with mock.patch("core.views.connections") as connections_mock:
            connections_mock.__getitem__.return_value.cursor.side_effect = OperationalError("down")
            response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["checks"]["database"], "error")

    def test_healthz_does_not_leak_configuration(self):
        body = self.client.get("/healthz").content.decode().lower()
        for leak in ["secret", "password", "dsn", "sqlite", "engine", "allowed_hosts", "token"]:
            self.assertNotIn(leak, body)


class SentryConfigurationTests(TestCase):
    """Error tracking must be entirely optional: the application has to start
    normally when SENTRY_DSN is unset, and must not crash when the SDK is
    missing or the DSN is malformed.

    TestCase (not SimpleTestCase) because the health probe below touches the
    database — SimpleTestCase blocks DB access and the probe correctly reports
    503 in that case."""

    def test_application_starts_without_sentry_configured(self):
        # The running test process is itself the evidence: settings imported and
        # the app is serving with no DSN configured.
        self.assertFalse(os.getenv("SENTRY_DSN", "").strip())
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)

    def test_settings_module_reimports_cleanly_with_no_dsn(self):
        spec = importlib.util.spec_from_file_location("_settings_no_dsn", settings_module_path())
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(os.environ, {"SENTRY_DSN": "", "DEBUG": "True"}, clear=False):
            spec.loader.exec_module(module)
        self.assertEqual(module.SENTRY_DSN, "")

    def test_invalid_dsn_does_not_prevent_startup(self):
        spec = importlib.util.spec_from_file_location("_settings_bad_dsn", settings_module_path())
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(
            os.environ, {"SENTRY_DSN": "not-a-valid-dsn", "DEBUG": "True"}, clear=False
        ):
            # Must not raise: a broken DSN cannot be allowed to take the site down.
            spec.loader.exec_module(module)
        self.assertEqual(module.SENTRY_DSN, "not-a-valid-dsn")

    def test_admins_env_var_is_parsed(self):
        spec = importlib.util.spec_from_file_location("_settings_admins", settings_module_path())
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(
            os.environ,
            {"ADMINS": "Ops Team <ops@example.com>, alerts@example.com", "DEBUG": "True"},
            clear=False,
        ):
            spec.loader.exec_module(module)
        self.assertEqual(
            module.ADMINS, [("Ops Team", "ops@example.com"), ("Admin", "alerts@example.com")]
        )


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class BackupScriptTests(SimpleTestCase):
    """The backup script is an operational deployment artifact; these assert the
    safety properties that make it trustworthy, not its exact wording."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.script = Path(settings.BASE_DIR) / "scripts" / "backup.sh"
        cls.body = cls.script.read_text(encoding="utf-8") if cls.script.exists() else ""

    def test_backup_script_exists(self):
        self.assertTrue(self.script.exists(), "scripts/backup.sh is missing")

    def test_script_fails_loudly(self):
        # Without these a failed copy would produce a silent, empty "backup".
        self.assertIn("set -euo pipefail", self.body)

    def test_script_excludes_env_file(self):
        self.assertIn("--exclude", self.body)
        self.assertIn(".env", self.body)

    def test_script_contains_no_secrets(self):
        for pattern in ["PASSWORD=", "SECRET_KEY=", "DSN=", "TOKEN="]:
            self.assertNotIn(pattern, self.body)

    def test_script_uses_sqlite_safe_copy(self):
        # A plain `cp` of a live SQLite file can capture a torn write.
        self.assertIn(".backup", self.body)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ProductionConfigTests(TestCase):
    def test_required_runtime_dependencies_are_declared(self):
        """Both back the production paths selected in config/settings.py:
        WhiteNoise serves static when DEBUG=False, and the Redis cache backend
        is selected whenever REDIS_URL is set."""
        with open("requirements.txt", encoding="utf-8") as handle:
            requirements = handle.read().lower()
        self.assertIn("whitenoise", requirements)
        self.assertIn("redis", requirements)

    def test_whitenoise_middleware_is_active_and_ordered(self):
        from django.conf import settings

        middleware = list(settings.MIDDLEWARE)
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", middleware)
        self.assertEqual(
            middleware.index("whitenoise.middleware.WhiteNoiseMiddleware"),
            middleware.index("django.middleware.security.SecurityMiddleware") + 1,
        )

    def test_staticfiles_backend_is_whitenoise(self):
        from django.conf import settings

        self.assertIn("whitenoise", settings.STORAGES["staticfiles"]["BACKEND"])
