from django.contrib import admin
from django import forms

from .models import Advertisement


class AdvertisementAdminForm(forms.ModelForm):
    class Meta:
        model = Advertisement
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean_html_code(self):
        html_code = self.cleaned_data.get("html_code", "")
        if html_code and self.request and not self.request.user.is_superuser:
            raise forms.ValidationError("Only Super Admin can create or edit raw HTML advertisements.")
        return html_code


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    form = AdvertisementAdminForm
    list_display = ("name", "placement", "active", "priority", "start_date", "end_date")
    list_filter = ("placement", "active")
    search_fields = ("name", "html_code")

    def get_form(self, request, obj=None, change=False, **kwargs):
        form_class = super().get_form(request, obj, change, **kwargs)

        class RequestAwareForm(form_class):
            def __init__(self, *args, **form_kwargs):
                form_kwargs["request"] = request
                super().__init__(*args, **form_kwargs)

        return RequestAwareForm

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.append("html_code")
        return readonly

# Register your models here.
