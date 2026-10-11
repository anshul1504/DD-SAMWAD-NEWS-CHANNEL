from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from news.models import Category


class WebStory(models.Model):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, allow_unicode=True)
    cover = models.ImageField(upload_to="webstories/covers/", blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    published_at = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)
    seo_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name_plural = "Web Stories"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("webstories:detail", args=[self.pk, self.public_url_slug])

    @property
    def public_url_slug(self):
        category = slugify(self.category.slug, allow_unicode=False) if self.category_id else ""
        return f"{category}-story" if category else "web-story"


class StorySlide(models.Model):
    story = models.ForeignKey(WebStory, on_delete=models.CASCADE, related_name="slides")
    image = models.ImageField(upload_to="webstories/slides/", blank=True)
    video = models.FileField(
        upload_to="webstories/slides/videos/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["mp4", "webm", "mov"])],
        help_text="Optional short vertical video for this slide. When set, it plays instead of the image.",
    )
    heading = models.CharField(max_length=180)
    text = models.TextField(blank=True)
    cta_label = models.CharField(max_length=80, blank=True)
    cta_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.heading

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if self.cta_url and (update_fields is None or "cta_url" in update_fields):
            self.cta_url = canonicalize_internal_article_url(self.cta_url)
        super().save(*args, **kwargs)


def canonicalize_internal_article_url(url):
    """Convert this site's legacy /news/<unicode-slug>/ links to canonical URLs.

    External links are intentionally untouched. Keeping this at the model edge
    also protects future stories created manually in admin or by import scripts.
    """
    parsed = urlsplit(url)
    site = urlsplit(settings.SITE_URL)
    if parsed.netloc and parsed.netloc.lower() != site.netloc.lower():
        return url
    decoded_path = unquote(parsed.path)
    parts = decoded_path.strip("/").split("/")
    if len(parts) != 2 or parts[0] != "news":
        return url

    from news.models import Article

    article = Article.objects.filter(slug=parts[1]).first()
    if not article:
        return url
    return f"{settings.SITE_URL.rstrip('/')}{article.get_absolute_url()}"

# Create your models here.
