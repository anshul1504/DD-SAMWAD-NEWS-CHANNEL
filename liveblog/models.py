from django.db import models
from django.urls import reverse
from django.utils import timezone

from locations.models import City
from news.models import Category


class LiveBlog(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live"
        ENDED = "ended", "Ended"

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, allow_unicode=True)
    description = models.TextField(blank=True)
    featured_image = models.ImageField(upload_to="liveblogs/", blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("liveblog:detail", args=[self.slug])


class LiveUpdate(models.Model):
    live_blog = models.ForeignKey(LiveBlog, on_delete=models.CASCADE, related_name="updates")
    heading = models.CharField(max_length=180)
    body = models.TextField()
    image = models.ImageField(upload_to="liveblogs/updates/", blank=True)
    video_url = models.URLField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    is_breaking = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return self.heading

# Create your models here.
