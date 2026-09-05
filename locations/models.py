from django.db import models
from django.urls import reverse


class State(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    seo_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("locations:state", args=[self.slug])


class District(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["state__name", "name"]
        unique_together = [("state", "slug")]

    def __str__(self):
        return f"{self.name}, {self.state.name}"

    def get_absolute_url(self):
        return reverse("locations:district", args=[self.state.slug, self.slug])


class City(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="cities")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["district__name", "name"]
        unique_together = [("district", "slug")]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("locations:city", args=[self.district.state.slug, self.district.slug, self.slug])

# Create your models here.
