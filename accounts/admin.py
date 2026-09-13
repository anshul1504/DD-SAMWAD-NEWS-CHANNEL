from django.contrib import admin

from .models import LoginOTP, ReporterProfile


@admin.register(ReporterProfile)
class ReporterProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "designation", "city", "active")
    list_filter = ("active", "city")
    search_fields = ("display_name", "user__username", "bio")
    prepopulated_fields = {"slug": ("display_name",)}
    autocomplete_fields = ("user", "city")


@admin.register(LoginOTP)
class LoginOTPAdmin(admin.ModelAdmin):
    # Read-only and code redacted: this exists so support can see delivery
    # failures (delivery_error, attempts) for stuck logins, never to read a
    # live OTP code out of the admin.
    list_display = ("email", "purpose", "masked_code", "delivered", "used", "attempts", "created_at")
    list_filter = ("purpose", "delivered", "used", "created_at")
    search_fields = ("email", "full_name", "ip_address")
    readonly_fields = [f.name for f in LoginOTP._meta.fields if f.name != "code"] + ["masked_code"]
    exclude = ("code",)

    @admin.display(description="Code")
    def masked_code(self, obj):
        return "••••••"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
