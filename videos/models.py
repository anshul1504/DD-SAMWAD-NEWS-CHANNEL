from django.db import models
from django.urls import reverse
from django.utils import timezone

from locations.models import City
from news.models import Category


class Video(models.Model):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, allow_unicode=True)
    thumbnail = models.ImageField(upload_to="videos/thumbs/", blank=True)
    youtube_url = models.URLField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    published_at = models.DateTimeField(default=timezone.now)
    views = models.PositiveIntegerField(default=0)
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

# Create your models here.
