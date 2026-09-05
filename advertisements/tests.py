from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission, User
from django.test import RequestFactory, TestCase, override_settings

from .admin import AdvertisementAdmin
from .models import Advertisement


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class AdvertisementAdminSecurityTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = AdvertisementAdmin(Advertisement, AdminSite())
        self.staff = User.objects.create_user("ads", "ads@example.com", "StrongPass123!", is_staff=True)
        self.staff.user_permissions.add(
            Permission.objects.get(codename="add_advertisement"),
            Permission.objects.get(codename="change_advertisement"),
            Permission.objects.get(codename="view_advertisement"),
        )
        self.superuser = User.objects.create_superuser("root", "root@example.com", "StrongPass123!")

    def _form_for(self, user, data):
        request = self.factory.post("/admin/advertisements/advertisement/add/", data)
        request.user = user
        form_class = self.admin.get_form(request)
        return form_class(data=data)

    def test_staff_cannot_manage_raw_html_field(self):
        request = self.factory.get("/admin/advertisements/advertisement/add/")
        request.user = self.staff
        self.assertIn("html_code", self.admin.get_readonly_fields(request))
        form = self._form_for(
            self.staff,
            {
                "name": "Unsafe ad",
                "ad_type": "html",
                "html_code": "<script>alert(1)</script>",
                "placement": Advertisement.Placement.HOME_TOP,
                "priority": 0,
                "active": "on",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("html_code", form.fields)

    def test_superuser_can_submit_raw_html_ad(self):
        form = self._form_for(
            self.superuser,
            {
                "name": "Trusted ad",
                "ad_type": "html",
                "html_code": "<div>Trusted creative</div>",
                "placement": Advertisement.Placement.HOME_TOP,
                "priority": 0,
                "active": "on",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)

# Create your tests here.
