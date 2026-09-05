from django import forms

from .models import ContactMessage, NewsletterSubscriber


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ("email", "name")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "ईमेल पता"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "नाम"}),
        }


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "subject", "message")
        widgets = {
            field: forms.TextInput(attrs={"class": "form-control"}) for field in ("name", "phone", "subject")
        } | {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }
