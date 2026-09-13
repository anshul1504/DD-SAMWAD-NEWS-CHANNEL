from django.contrib.auth.models import Group, Permission, User
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from news.models import Article, Bookmark, Category

from .models import LoginOTP
from .views import LOGIN_MAX_FAILURES_PER_EMAIL


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

    def test_unknown_email_login_does_not_reveal_account_absence(self):
        """Replaces an earlier test that asserted "No active account found" was
        shown for unknown addresses. That message was an enumeration oracle
        (F-010); the flow must now be indistinguishable from a real account.
        Still asserts the important part: no OTP is created and no mail is sent
        for an address that does not exist."""
        response = self.client.post(reverse("accounts:login"), {"email": "missing@example.com"})
        self.assertRedirects(response, reverse("accounts:verify_otp"))
        self.assertEqual(LoginOTP.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

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


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class UserEnumerationTests(TestCase):
    """Login and password reset must not reveal which addresses are registered."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="real@example.com", email="real@example.com", password="StrongPass123!"
        )

    def tearDown(self):
        cache.clear()

    def test_login_otp_response_identical_for_known_and_unknown_email(self):
        known = self.client.post(reverse("accounts:login"), {"email": self.user.email})
        self.client.logout()
        cache.clear()
        unknown = self.client.post(reverse("accounts:login"), {"email": "nobody@example.com"})

        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known["Location"], unknown["Location"])

    def test_forgot_password_response_identical_for_known_and_unknown_email(self):
        known = self.client.post(reverse("accounts:forgot_password"), {"email": self.user.email})
        cache.clear()
        unknown = self.client.post(reverse("accounts:forgot_password"), {"email": "nobody@example.com"})

        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known["Location"], unknown["Location"])

    def test_no_otp_or_mail_generated_for_unknown_address(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": "nobody@example.com"})
        self.assertEqual(LoginOTP.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_verify_page_renders_for_unknown_address_and_rejects_any_code(self):
        # The decoy path must look like the real one all the way through.
        self.client.post(reverse("accounts:login"), {"email": "nobody@example.com"})
        page = self.client.get(reverse("accounts:verify_otp"))
        self.assertEqual(page.status_code, 200)

        response = self.client.post(reverse("accounts:verify_otp"), {"code": "123456"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_wrong_password_error_does_not_name_the_reason(self):
        response = self.client.post(
            reverse("accounts:login"), {"email": self.user.email, "password": "WrongPass123!"}
        )
        self.assertContains(response, "Invalid email or password")
        self.assertNotContains(response, "No active account found")
        self.assertNotContains(response, "Incorrect password")

    def test_unknown_email_password_attempt_gives_same_error(self):
        response = self.client.post(
            reverse("accounts:login"), {"email": "nobody@example.com", "password": "WrongPass123!"}
        )
        self.assertContains(response, "Invalid email or password")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class PasswordLoginThrottleTests(TestCase):
    """The OTP branch was throttled but the password branch was not, leaving an
    unlimited online password-guessing side door."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="target@example.com", email="target@example.com", password="StrongPass123!"
        )

    def tearDown(self):
        cache.clear()

    def _attempt(self, password, **extra):
        return self.client.post(
            reverse("accounts:login"), {"email": self.user.email, "password": password}, **extra
        )

    def test_repeated_failures_are_blocked(self):
        for _ in range(LOGIN_MAX_FAILURES_PER_EMAIL):
            self._attempt("WrongPass123!")
        response = self._attempt("WrongPass123!")
        self.assertContains(response, "Too many failed sign-in attempts")

    def test_correct_password_still_works_after_a_few_failures(self):
        # Quota is consumed only on failure, so a legitimate user who mistypes
        # once or twice must not be locked out.
        self._attempt("WrongPass123!")
        self._attempt("WrongPass123!")
        response = self._attempt("StrongPass123!")
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_successful_login_consumes_no_quota(self):
        for _ in range(LOGIN_MAX_FAILURES_PER_EMAIL + 2):
            self.client.post(
                reverse("accounts:login"), {"email": self.user.email, "password": "StrongPass123!"}
            )
            self.client.logout()
        response = self._attempt("StrongPass123!")
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_throttle_blocks_even_with_correct_password_once_exceeded(self):
        for _ in range(LOGIN_MAX_FAILURES_PER_EMAIL):
            self._attempt("WrongPass123!")
        response = self._attempt("StrongPass123!")
        self.assertContains(response, "Too many failed sign-in attempts")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_spoofed_forwarded_for_does_not_reset_ip_quota(self):
        # Leftmost X-Forwarded-For is client-supplied; rotating it must not help.
        for index in range(LOGIN_MAX_FAILURES_PER_EMAIL):
            self._attempt("WrongPass123!", HTTP_X_FORWARDED_FOR=f"9.9.9.{index}, 127.0.0.1")
        response = self._attempt("WrongPass123!", HTTP_X_FORWARDED_FOR="8.8.8.8, 127.0.0.1")
        self.assertContains(response, "Too many failed sign-in attempts")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class PasswordResetSessionInvalidationTests(TestCase):
    """Resetting a password is what a compromised user does to lock an attacker
    out, so a pre-existing session must not survive it.

    Two layers are involved. Django already rejects old sessions after a password
    change via the session auth hash, so the *authentication* assertion below
    passes even without our explicit flush. The flush adds the part Django does
    not do: deleting the stale session rows immediately instead of leaving them
    in the table until they expire. Both are asserted separately."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="victim@example.com", email="victim@example.com", password="OldStrongPass123!"
        )

    def tearDown(self):
        cache.clear()

    def test_existing_session_is_invalidated_by_reset(self):
        attacker = Client()
        attacker.force_login(self.user)
        self.assertIn("_auth_user_id", attacker.session)
        # Confirm the hijacked session really is authenticated first.
        self.assertEqual(attacker.get(reverse("accounts:dashboard")).status_code, 200)

        victim = Client()
        victim.post(reverse("accounts:forgot_password"), {"email": self.user.email})
        otp = LoginOTP.objects.get(email=self.user.email, purpose=LoginOTP.Purpose.PASSWORD_RESET)
        victim.post(reverse("accounts:verify_otp"), {"code": otp.code})
        response = victim.post(
            reverse("accounts:reset_password"),
            {"password": "BrandNewPass456!", "confirm_password": "BrandNewPass456!"},
        )
        self.assertRedirects(response, reverse("accounts:login"))

        # The attacker's previously valid session must no longer authenticate.
        followed = attacker.get(reverse("accounts:dashboard"))
        self.assertEqual(followed.status_code, 302)
        self.assertIn(reverse("accounts:login"), followed["Location"])

    def test_reset_deletes_the_stale_session_row(self):
        """This is the part Django's session auth hash does not do: without the
        explicit flush the row lingers in django_session until it expires."""
        attacker = Client()
        attacker.force_login(self.user)
        stale_key = attacker.session.session_key
        self.assertTrue(Session.objects.filter(session_key=stale_key).exists())

        victim = Client()
        victim.post(reverse("accounts:forgot_password"), {"email": self.user.email})
        otp = LoginOTP.objects.get(email=self.user.email, purpose=LoginOTP.Purpose.PASSWORD_RESET)
        victim.post(reverse("accounts:verify_otp"), {"code": otp.code})
        victim.post(
            reverse("accounts:reset_password"),
            {"password": "BrandNewPass456!", "confirm_password": "BrandNewPass456!"},
        )

        self.assertFalse(Session.objects.filter(session_key=stale_key).exists())

    def test_password_is_actually_changed_and_otp_login_still_works(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": self.user.email})
        otp = LoginOTP.objects.get(email=self.user.email, purpose=LoginOTP.Purpose.PASSWORD_RESET)
        self.client.post(reverse("accounts:verify_otp"), {"code": otp.code})
        self.client.post(
            reverse("accounts:reset_password"),
            {"password": "BrandNewPass456!", "confirm_password": "BrandNewPass456!"},
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPass456!"))

        # OTP login must not be broken by the session flush.
        cache.clear()
        fresh = Client()
        fresh.post(reverse("accounts:login"), {"email": self.user.email})
        login_otp = LoginOTP.objects.filter(
            email=self.user.email, purpose=LoginOTP.Purpose.LOGIN
        ).first()
        response = fresh.post(reverse("accounts:verify_otp"), {"code": login_otp.code})
        self.assertRedirects(response, reverse("accounts:dashboard"))


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class PortalScreenTests(TestCase):
    """Every portal screen 500'd when its template was deleted, and the failure
    was invisible until a request hit it. These assert each one renders."""

    def setUp(self):
        cache.clear()
        self.editor = User.objects.create_user(username="desk", password="StrongPass123!")
        self.editor.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="news",
                codename__in=["view_article", "add_article", "change_article", "delete_article"],
            )
        )
        self.category = Category.objects.create(name="National", hindi_name="देश", slug="national")
        self.article = Article.objects.create(
            title="Portal story",
            body="<p>Body</p>",
            category=self.category,
            author=self.editor,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.client.force_login(self.editor)

    def tearDown(self):
        cache.clear()

    def test_dashboard_renders(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Newsroom Command")

    def test_signup_page_renders(self):
        self.client.logout()
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Join the portal")

    def test_module_list_renders_with_records(self):
        response = self.client.get(reverse("accounts:portal_module", args=["articles"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Portal story")

    def test_module_list_search_filters(self):
        response = self.client.get(reverse("accounts:portal_module", args=["articles"]), {"q": "nomatch"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Portal story")

    def test_module_new_form_renders(self):
        response = self.client.get(reverse("accounts:portal_module_new", args=["articles"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New Articles")

    def test_module_edit_form_renders(self):
        response = self.client.get(reverse("accounts:portal_module_edit", args=["articles", self.article.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Articles")

    def test_module_without_form_fields_cannot_be_edited(self):
        # "users" is deliberately list-only; a generic ModelForm would store
        # plaintext passwords and bypass is_staff/is_superuser safeguards.
        response = self.client.get(reverse("accounts:portal_module_new", args=["users"]))
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_unknown_module_redirects(self):
        response = self.client.get(reverse("accounts:portal_module", args=["nope"]))
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_portal_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("accounts:portal_module", args=["articles"]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class PortalDeleteArchivesTests(TestCase):
    """Portal delete used to call instance.delete() for any model without an
    `active` field. Article has no `active` field, so a single click destroyed a
    published story and cascaded its bookmarks."""

    def setUp(self):
        cache.clear()
        self.editor = User.objects.create_user(username="desk", password="StrongPass123!")
        self.editor.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="news",
                codename__in=["view_article", "change_article", "delete_article"],
            )
        )
        self.reader = User.objects.create_user(username="reader", password="StrongPass123!")
        self.category = Category.objects.create(name="National", hindi_name="देश", slug="national")
        self.article = Article.objects.create(
            title="Story to remove",
            body="<p>Original body</p>",
            category=self.category,
            author=self.editor,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.bookmark = Bookmark.objects.create(user=self.reader, article=self.article)
        self.client.force_login(self.editor)

    def tearDown(self):
        cache.clear()

    def test_article_delete_archives_and_preserves_row(self):
        response = self.client.post(
            reverse("accounts:portal_module_delete", args=["articles", self.article.pk])
        )
        self.assertRedirects(response, reverse("accounts:portal_module", args=["articles"]))

        self.assertTrue(Article.objects.filter(pk=self.article.pk).exists())
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.ARCHIVED)
        self.assertIn("Original body", self.article.body)
        self.assertEqual(self.article.author, self.editor)
        self.assertEqual(self.article.category, self.category)

    def test_archived_article_keeps_bookmarks(self):
        self.client.post(reverse("accounts:portal_module_delete", args=["articles", self.article.pk]))
        self.assertTrue(Bookmark.objects.filter(pk=self.bookmark.pk).exists())

    def test_archived_article_leaves_public_site(self):
        self.client.post(reverse("accounts:portal_module_delete", args=["articles", self.article.pk]))
        self.assertEqual(self.client.get(self.article.get_absolute_url()).status_code, 404)

    def test_delete_requires_post(self):
        response = self.client.get(
            reverse("accounts:portal_module_delete", args=["articles", self.article.pk])
        )
        self.assertEqual(response.status_code, 405)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.PUBLISHED)

    def test_delete_requires_permission(self):
        self.client.force_login(self.reader)
        response = self.client.post(
            reverse("accounts:portal_module_delete", args=["articles", self.article.pk])
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.PUBLISHED)

    def test_model_with_active_flag_is_deactivated_not_deleted(self):
        self.editor.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="news",
                codename__in=["view_category", "change_category", "delete_category"],
            )
        )
        self.editor = User.objects.get(pk=self.editor.pk)  # drop cached permissions
        self.client.force_login(self.editor)
        self.client.post(reverse("accounts:portal_module_delete", args=["categories", self.category.pk]))
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
        self.category.refresh_from_db()
        self.assertFalse(self.category.active)
