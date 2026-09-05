from django.contrib import admin

from .models import ContactMessage, NewsletterSubscriber, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Branding", {"fields": ("site_name", "tagline", "logo", "favicon", "footer_description")}),
        ("Contact", {"fields": ("email", "primary_phone", "address")}),
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

# Register your models here.
