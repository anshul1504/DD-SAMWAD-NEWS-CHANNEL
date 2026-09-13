from django.contrib import admin

from .models import CareerApplication, ContactMessage, EPaperEdition, EPaperPage, JobOpening, NewsletterSubscriber, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Branding", {"fields": ("site_name", "tagline", "logo", "favicon", "footer_description")}),
        ("Contact", {"fields": ("email", "primary_phone", "address")}),
        ("Routed Inboxes", {
            "fields": (
                "grievance_email", "editorial_email", "advertise_email", "sponsorship_email",
                "investor_email", "careers_email", "tips_email", "privacy_email",
            ),
            "description": "Each falls back to the General email above when left blank.",
        }),
        ("Social", {"fields": ("facebook_url", "instagram_url", "youtube_url", "twitter_url", "telegram_url", "whatsapp_url")}),
        ("Analytics", {"fields": ("google_analytics_id", "search_console_verification")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "active", "subscribed_at")
    list_filter = ("active", "subscribed_at")
    search_fields = ("email", "name")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "created_at", "resolved")
    list_filter = ("resolved", "created_at")
    search_fields = ("name", "email", "subject", "message")


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "location", "employment_type", "active", "posted_at")
    list_filter = ("active", "employment_type")
    search_fields = ("title", "department", "location")


@admin.register(CareerApplication)
class CareerApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "job", "role_applied", "created_at", "reviewed")
    list_filter = ("reviewed", "created_at")
    search_fields = ("name", "email", "role_applied")


class EPaperPageInline(admin.TabularInline):
    model = EPaperPage
    extra = 1
    ordering = ("page_number",)


@admin.register(EPaperEdition)
class EPaperEditionAdmin(admin.ModelAdmin):
    list_display = ("edition_date", "city", "title", "page_count", "active", "created_at")
    list_filter = ("active", "city")
    date_hierarchy = "edition_date"
    search_fields = ("title", "city__name")
    autocomplete_fields = ("city",)
    inlines = [EPaperPageInline]

# Register your models here.
