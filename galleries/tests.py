from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Gallery


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class GalleryPublicUrlTests(TestCase):
    def test_unicode_database_slug_has_clean_url_and_old_link_redirects(self):
        gallery = Gallery.objects.create(title="हिंदी गैलरी", slug="हिंदी-गैलरी", active=True)

        self.assertEqual(gallery.get_absolute_url(), f"/photos/{gallery.pk}/photo-gallery/")
        self.assertTrue(gallery.get_absolute_url().isascii())
        legacy = self.client.get(reverse("galleries:legacy_detail", args=[gallery.slug]))
        self.assertRedirects(legacy, gallery.get_absolute_url(), status_code=301, fetch_redirect_response=False)
        wrong = self.client.get(reverse("galleries:detail", args=[gallery.pk, "wrong-label"]))
        self.assertRedirects(wrong, gallery.get_absolute_url(), status_code=301, fetch_redirect_response=False)

# Create your tests here.
