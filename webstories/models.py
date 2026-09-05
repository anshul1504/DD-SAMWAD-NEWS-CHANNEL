from django.db import models
from django.urls import reverse
from django.utils import timezone

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
        return reverse("webstories:detail", args=[self.slug])


class StorySlide(models.Model):
    story = models.ForeignKey(WebStory, on_delete=models.CASCADE, related_name="slides")
    image = models.ImageField(upload_to="webstories/slides/", blank=True)
    heading = models.CharField(max_length=180)
    text = models.TextField(blank=True)
    cta_label = models.CharField(max_length=80, blank=True)
    cta_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.heading

# Create your models here.
