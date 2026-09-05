from django.contrib import admin

from .models import City, District, State


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "active")
    list_filter = ("state", "active")
    search_fields = ("name", "slug", "state__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("state",)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "active")
    list_filter = ("district__state", "active")
    search_fields = ("name", "slug", "district__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("district",)

# Register your models here.
