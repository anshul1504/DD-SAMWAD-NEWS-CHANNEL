from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.youtube import youtube_embed_url
from locations.models import City
from news.models import Category

# Re-exported for backwards compatibility with existing imports
# (`from videos.models import youtube_embed_url`); the real implementation
# now lives in core.youtube so other apps (news, liveblog, webstories) can
# use it without importing videos, which itself imports news.models and
# would otherwise create a circular import.
__all__ = ["Video", "youtube_embed_url"]


class Video(models.Model):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, allow_unicode=True)
    thumbnail = models.ImageField(upload_to="videos/thumbs/", blank=True)
    youtube_url = models.URLField(
        help_text="कोई भी YouTube लिंक चलेगा — Watch, Shorts, Share (?si=...) या Embed लिंक, जो भी कॉपी करें।",
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    published_at = models.DateTimeField(default=timezone.now)
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    # Long-form videos play inline on the /videos/ grid; Shorts open the
    # full-screen swipe viewer -- a real editorial choice per upload, not a
    # cosmetic split, so it has to be a field a newsroom editor actually sets.
    is_short = models.BooleanField(default=False, verbose_name="Short/Reel वीडियो है")
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    seo_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("videos:detail", args=[self.slug])

    @property
    def embed_url(self):
        return youtube_embed_url(self.youtube_url)


class VideoComment(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="comments")
    name = models.CharField(max_length=80)
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    # Visible immediately (the point of a "live" comment section) but rate
    # limited + honeypot-guarded in the form/view, and editors can still
    # un-approve (hide) a comment from admin without deleting it.
    approved = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}: {self.text[:40]}"


class VideoLike(models.Model):
    """One row per (video, visitor). Lets the like button toggle correctly on
    refresh without accounts -- the visitor is identified by a hashed IP, same
    approach as the comment/contact-form throttling already used in this app."""

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="video_likes")
    ip_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["video", "ip_hash"], name="unique_video_like_per_visitor"),
        ]
