from django.contrib import admin

from .models import ReporterProfile


@admin.register(ReporterProfile)
class ReporterProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "designation", "city", "active")
    list_filter = ("active", "city")
    search_fields = ("display_name", "user__username", "bio")
    prepopulated_fields = {"slug": ("display_name",)}
    autocomplete_fields = ("user", "city")

# Register your models here.
