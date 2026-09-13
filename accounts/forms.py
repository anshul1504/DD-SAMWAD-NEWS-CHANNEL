from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password


User = get_user_model()


class EmailLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "Enter your work email", "autocomplete": "email"}))
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Password (optional — leave blank for OTP)", "autocomplete": "current-password"}),
    )

    def clean_email(self):
        # Deliberately does NOT check whether the account exists. Rejecting
        # unknown addresses here turned the form into an account-enumeration
        # oracle; the view now returns an identical response either way.
        return self.cleaned_data["email"].strip().lower()


class SignupForm(forms.Form):
    full_name = forms.CharField(max_length=160, widget=forms.TextInput(attrs={"placeholder": "Full name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "Enter your email", "autocomplete": "email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Create password", "autocomplete": "new-password"}))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already exists with this email.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password


class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={"placeholder": "000000", "inputmode": "numeric", "autocomplete": "one-time-code"}),
    )

    def clean_code(self):
        code = "".join(ch for ch in self.cleaned_data["code"] if ch.isdigit())
        if len(code) != 6:
            raise forms.ValidationError("Enter the 6 digit OTP.")
        return code


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "Enter your registered email"}))

    def clean_email(self):
        # See EmailLoginForm.clean_email — existence is deliberately not checked.
        return self.cleaned_data["email"].strip().lower()


class ResetPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "New password", "autocomplete": "new-password"}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Confirm password", "autocomplete": "new-password"}))

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("confirm_password") and cleaned["password"] != cleaned["confirm_password"]:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned
