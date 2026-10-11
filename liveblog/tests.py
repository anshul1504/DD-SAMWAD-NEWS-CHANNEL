from django.test import TestCase, override_settings
from django.urls import reverse

from .models import LiveBlog


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class LiveBlogPublicUrlTests(TestCase):
    def test_unicode_database_slug_has_clean_url_and_old_link_redirects(self):
        liveblog = LiveBlog.objects.create(title="हिंदी लाइव", slug="हिंदी-लाइव", active=True)

        self.assertEqual(liveblog.get_absolute_url(), f"/live/{liveblog.pk}/live-update/")
        self.assertTrue(liveblog.get_absolute_url().isascii())
        legacy = self.client.get(reverse("liveblog:legacy_detail", args=[liveblog.slug]))
        self.assertRedirects(legacy, liveblog.get_absolute_url(), status_code=301, fetch_redirect_response=False)
        wrong = self.client.get(reverse("liveblog:detail", args=[liveblog.pk, "wrong-label"]))
        self.assertRedirects(wrong, liveblog.get_absolute_url(), status_code=301, fetch_redirect_response=False)

# Create your tests here.
