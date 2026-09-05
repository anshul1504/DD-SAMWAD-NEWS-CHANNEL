from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from locations.models import City


class ReporterProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reporter_profile")
    display_name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    profile_photo = models.ImageField(upload_to="authors/", blank=True)
    designation = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    email_public = models.EmailField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name

    def get_absolute_url(self):
        return reverse("accounts:author_detail", args=[self.slug])


class LoginOTP(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"
        SIGNUP = "signup", "Signup"
        PASSWORD_RESET = "password_reset", "Password Reset"

    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=160, blank=True)
    used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    delivered = models.BooleanField(default=False)
    delivery_error = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "purpose", "used"]),
        ]

    def __str__(self):
        return f"{self.email} {self.purpose}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def can_verify(self):
        return not self.used and not self.is_expired and self.attempts < 5
