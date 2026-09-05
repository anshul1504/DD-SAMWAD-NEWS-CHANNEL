from django.contrib.auth.models import Group
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import LoginOTP


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class PortalAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.guest_group = Group.objects.create(name="Guest")
        self.user = self._user_model().objects.create_user(
            username="editor@example.com",
            email="editor@example.com",
            password="StrongPass123!",
        )

    def tearDown(self):
        cache.clear()

    @staticmethod
    def _user_model():
        from django.contrib.auth import get_user_model

        return get_user_model()

    def test_successful_otp_login(self):
        response = self.client.post(reverse("accounts:login"), {"email": self.user.email})
        self.assertRedirects(response, reverse("accounts:verify_otp"))
        self.assertEqual(len(mail.outbox), 1)
        otp = LoginOTP.objects.get(email=self.user.email, purpose=LoginOTP.Purpose.LOGIN)

        response = self.client.post(reverse("accounts:verify_otp"), {"code": otp.code})
        self.assertRedirects(response, reverse("accounts:dashboard"))
        otp.refresh_from_db()
        self.assertTrue(otp.used)
        self.assertIsNotNone(otp.verified_at)

    def test_unknown_email_login_is_rejected(self):
        response = self.client.post(reverse("accounts:login"), {"email": "missing@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No active account found")
        self.assertEqual(LoginOTP.objects.count(), 0)

    def test_expired_otp_redirects_to_login(self):
        otp = LoginOTP.objects.create(
            email=self.user.email,
            user=self.user,
            code="123456",
            purpose=LoginOTP.Purpose.LOGIN,
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        session = self.client.session
        session["pending_otp_id"] = otp.pk
        session.save()

        response = self.client.post(reverse("accounts:verify_otp"), {"code": "123456"})
        self.assertRedirects(response, reverse("accounts:login"))

    def test_incorrect_otp_tracks_attempts_and_limit(self):
        otp = LoginOTP.objects.create(
            email=self.user.email,
            user=self.user,
            code="123456",
            purpose=LoginOTP.Purpose.LOGIN,
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        session = self.client.session
        session["pending_otp_id"] = otp.pk
        session.save()

        for _ in range(5):
            self.client.post(reverse("accounts:verify_otp"), {"code": "000000"})
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 5)
        response = self.client.post(reverse("accounts:verify_otp"), {"code": "123456"})
        self.assertRedirects(response, reverse("accounts:login"))

    def test_resend_cooldown(self):
        self.client.post(reverse("accounts:login"), {"email": self.user.email})
        response = self.client.post(reverse("accounts:login"), {"email": self.user.email})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please wait before requesting another OTP")

    def test_signup_creates_guest_after_otp_without_session_password(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {"full_name": "Guest User", "email": "guest@example.com", "password": "StrongPass123!"},
        )
        self.assertRedirects(response, reverse("accounts:verify_otp"))
        pending_user = self._user_model().objects.get(email="guest@example.com")
        self.assertFalse(pending_user.is_active)
        self.assertNotIn("signup_password", self.client.session)

        otp = LoginOTP.objects.get(email="guest@example.com", purpose=LoginOTP.Purpose.SIGNUP)
        response = self.client.post(reverse("accounts:verify_otp"), {"code": otp.code})
        self.assertRedirects(response, reverse("accounts:dashboard"))
        pending_user.refresh_from_db()
        self.assertTrue(pending_user.is_active)
        self.assertTrue(pending_user.groups.filter(name="Guest").exists())

    def test_forgot_password_and_reset(self):
        response = self.client.post(reverse("accounts:forgot_password"), {"email": self.user.email})
        self.assertRedirects(response, reverse("accounts:verify_otp"))
        otp = LoginOTP.objects.get(email=self.user.email, purpose=LoginOTP.Purpose.PASSWORD_RESET)
        response = self.client.post(reverse("accounts:verify_otp"), {"code": otp.code})
        self.assertRedirects(response, reverse("accounts:reset_password"))
        response = self.client.post(
            reverse("accounts:reset_password"),
            {"password": "NewStrongPass123!", "confirm_password": "NewStrongPass123!"},
        )
        self.assertRedirects(response, reverse("accounts:login"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass123!"))

    def test_logout_redirects_to_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_unauthorized_module_access_redirects(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:portal_module", args=["users"]))
        self.assertRedirects(response, reverse("accounts:dashboard"))

# Create your tests here.
