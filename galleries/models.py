from django.db import models
from django.urls import reverse
from django.utils import timezone

from locations.models import City
from news.models import Category


class Gallery(models.Model):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, allow_unicode=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    cover_image = models.ImageField(upload_to="galleries/covers/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)
    seo_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name_plural = "Galleries"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("galleries:detail", args=[self.slug])


class GalleryImage(models.Model):
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="galleries/images/")
    caption = models.CharField(max_length=220, blank=True)
    credit = models.CharField(max_length=120, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.caption or self.gallery.title

# Create your models here.
