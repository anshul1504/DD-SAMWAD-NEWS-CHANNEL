from django import forms

from .models import VideoComment


class VideoCommentForm(forms.ModelForm):
    # Honeypot: same pattern as ContactForm -- hidden from real users, but a
    # bot that fills every field populates it, and that's rejected silently.
    website = forms.CharField(
        required=False,
        label="Website",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1", "aria-hidden": "true"}),
    )

    class Meta:
        model = VideoComment
        fields = ("name", "text")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "आपका नाम", "maxlength": 80}),
            "text": forms.Textarea(attrs={"placeholder": "अपनी प्रतिक्रिया लिखें...", "rows": 2, "maxlength": 500}),
        }

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Invalid submission.")
        return ""
