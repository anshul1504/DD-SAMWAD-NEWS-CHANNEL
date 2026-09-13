from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class SiteSettings(models.Model):
    site_name = models.CharField(max_length=150, default="Desh Darpan Samvad")
    tagline = models.CharField(max_length=200, blank=True, default="सच, सरोकार और संवाद")
    logo = models.ImageField(upload_to="branding/", blank=True)
    favicon = models.ImageField(upload_to="branding/", blank=True)
    email = models.EmailField(blank=True, help_text="General inbox, used as the fallback for every role below.")
    # Routing addresses so each page's complaint/query reaches the right
    # inbox instead of everything landing in one general mailbox. Each falls
    # back to `email` above when left blank.
    grievance_email = models.EmailField(blank=True, help_text="Grievance Officer inbox (IT Rules 2021). Falls back to General email.")
    editorial_email = models.EmailField(blank=True, help_text="Correction requests / editorial queries. Falls back to General email.")
    advertise_email = models.EmailField(blank=True, help_text="Advertising enquiries. Falls back to General email.")
    sponsorship_email = models.EmailField(blank=True, help_text="Sponsorship / brand partnership enquiries. Falls back to General email.")
    investor_email = models.EmailField(blank=True, help_text="Investor relations enquiries. Falls back to General email.")
    careers_email = models.EmailField(blank=True, help_text="Job applications. Falls back to General email.")
    tips_email = models.EmailField(blank=True, help_text="News tips / leads. Falls back to General email.")
    privacy_email = models.EmailField(blank=True, help_text="Data access/deletion requests. Falls back to General email.")
    primary_phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    telegram_url = models.URLField(blank=True)
    whatsapp_url = models.URLField(blank=True)
    footer_description = models.TextField(blank=True)
    google_analytics_id = models.CharField(max_length=60, blank=True)
    search_console_verification = models.CharField(max_length=120, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def routed_email(self, role):
        """Address for a specific role (grievance/editorial/advertise/careers/
        tips/privacy), falling back to the general inbox when unset."""
        return getattr(self, f"{role}_email", "") or self.email


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120, blank=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=160)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject


class JobOpening(models.Model):
    """Editorial-managed vacancy so the Careers page never has to fabricate
    listings — with none active it shows an honest empty state instead."""

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        INTERNSHIP = "internship", "Internship"
        FREELANCE = "freelance", "Freelance / Stringer"

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    department = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    posted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-posted_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "role"
            slug = base_slug
            suffix = 2
            while JobOpening.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:job_detail", args=[self.slug])


def _resume_upload_path(instance, filename):
    return f"career_applications/{filename}"


class CareerApplication(models.Model):
    job = models.ForeignKey(JobOpening, on_delete=models.SET_NULL, null=True, blank=True, related_name="applications")
    role_applied = models.CharField(max_length=160, blank=True, help_text="Used when no specific opening is selected.")
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    cover_note = models.TextField(blank=True)
    resume = models.FileField(
        upload_to=_resume_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"])],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.role_applied or (self.job.title if self.job else 'General')}"


class EPaperEdition(models.Model):
    """A real, editor-uploaded daily PDF edition. Deliberately not fabricated:
    with no editions uploaded, the e-paper page shows an honest empty state
    instead of a link to a non-existent issue.

    `city` is null for the main/default edition; a real per-city edition
    (Indore, Ujjain, ...) is its own row for the same date, so a newsroom
    that actually prints local editions can upload each one separately --
    the "Local Editions" strip only ever lists cities that have a real
    upload, never a fabricated city list."""

    edition_date = models.DateField()
    city = models.ForeignKey("locations.City", on_delete=models.CASCADE, null=True, blank=True, related_name="epaper_editions")
    title = models.CharField(max_length=160, blank=True, help_text='e.g. "इंदौर संस्करण". Optional.')
    pdf = models.FileField(
        upload_to="epaper/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    cover_image = models.ImageField(upload_to="epaper/covers/", blank=True)
    page_count = models.PositiveIntegerField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-edition_date"]
        constraints = [
            models.UniqueConstraint(fields=["edition_date", "city"], name="unique_epaper_edition_per_city_date"),
        ]

    def __str__(self):
        label = self.city.name if self.city else (self.title or "ई-पेपर")
        return f"{label} - {self.edition_date}"


class EPaperPage(models.Model):
    """One rendered page image per edition. The in-site reader shows these
    images with page-by-page navigation instead of embedding the raw PDF --
    browser PDF viewers render inconsistently (or not at all) inside an
    iframe depending on browser/OS/mobile webview, while a plain image never
    fails to display. The PDF itself is kept only for the download button."""

    edition = models.ForeignKey(EPaperEdition, on_delete=models.CASCADE, related_name="pages")
    page_number = models.PositiveIntegerField()
    image = models.ImageField(upload_to="epaper/pages/")

    class Meta:
        ordering = ["page_number"]
        constraints = [
            models.UniqueConstraint(fields=["edition", "page_number"], name="unique_epaper_page_number"),
        ]

    def __str__(self):
        return f"{self.edition} - पेज {self.page_number}"
