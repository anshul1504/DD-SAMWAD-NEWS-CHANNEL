from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "location", "published_at", "views", "featured", "active")
    list_filter = ("active", "featured", "category", "published_at")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}

# Register your models here.
