from django.contrib import admin

from .models import LiveBlog, LiveUpdate


class LiveUpdateInline(admin.StackedInline):
    model = LiveUpdate
    extra = 1


@admin.register(LiveBlog)
class LiveBlogAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "category", "location", "start_time", "active")
    list_filter = ("status", "active", "category")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = (LiveUpdateInline,)

# Register your models here.
