from django.contrib import admin

from .models import StorySlide, WebStory


class StorySlideInline(admin.TabularInline):
    model = StorySlide
    extra = 1


@admin.register(WebStory)
class WebStoryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "published_at", "active")
    list_filter = ("active", "category", "published_at")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = (StorySlideInline,)

# Register your models here.
