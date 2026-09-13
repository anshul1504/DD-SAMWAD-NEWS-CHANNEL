from django.contrib import admin

from .models import Video, VideoComment, VideoLike


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "location", "published_at", "views", "likes", "is_short", "featured", "active")
    list_filter = ("active", "is_short", "featured", "category", "published_at")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    list_display = ("video", "name", "text", "created_at", "approved")
    list_filter = ("approved", "created_at")
    search_fields = ("name", "text", "video__title")
    actions = ["approve_comments"]

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        queryset.update(approved=True)

# Register your models here.
