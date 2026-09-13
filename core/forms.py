from django import forms

from .models import CareerApplication, ContactMessage, NewsletterSubscriber

CAREER_RESUME_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ("email", "name")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "ईमेल पता"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "नाम"}),
        }


class ContactForm(forms.ModelForm):
    # Honeypot: hidden from users via CSS/aria, but bots that fill every input
    # will populate it. A non-empty value fails validation with the same generic
    # error a human would never see.
    website = forms.CharField(
        required=False,
        label="Website",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1", "aria-hidden": "true"}),
    )

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "subject", "message")
        widgets = {
            field: forms.TextInput(attrs={"class": "form-control"}) for field in ("name", "phone", "subject")
        } | {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Invalid submission.")
        return ""


class CareerApplicationForm(forms.ModelForm):
    website = forms.CharField(
        required=False,
        label="Website",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1", "aria-hidden": "true"}),
    )

    class Meta:
        model = CareerApplication
        fields = ("job", "role_applied", "name", "email", "phone", "cover_note", "resume")
        widgets = {
            "job": forms.Select(attrs={"class": "form-control"}),
            "role_applied": forms.TextInput(attrs={"class": "form-control", "placeholder": "जैसे: रिपोर्टर, इंदौर"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "cover_note": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "resume": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".pdf,.doc,.docx"}),
        }

    def __init__(self, *args, job=None, **kwargs):
        """`job` locks the application to one opening (from its detail page):
        the field is hidden rather than left as a picker second-guessing the
        page the visitor is already on. Without it (the general-application
        page), the field is dropped entirely and `role_applied` is required."""
        super().__init__(*args, **kwargs)
        if job is not None:
            self.fields["job"].widget = forms.HiddenInput()
            self.fields["job"].initial = job.pk
            self.fields["role_applied"].widget = forms.HiddenInput()
            self.fields["role_applied"].required = False
        else:
            del self.fields["job"]
            self.fields["role_applied"].required = True
            self.fields["role_applied"].widget.attrs["placeholder"] = "जैसे: रिपोर्टर, इंदौर"

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Invalid submission.")
        return ""

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("job") and not cleaned.get("role_applied"):
            self.add_error("role_applied", "कृपया कोई पद चुनें या भूमिका लिखें।")
        return cleaned

    def clean_resume(self):
        resume = self.cleaned_data["resume"]
        if resume.size > CAREER_RESUME_MAX_BYTES:
            raise forms.ValidationError("फ़ाइल का आकार 5MB से कम होना चाहिए।")
        return resume
