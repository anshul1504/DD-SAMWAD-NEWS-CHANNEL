import random
import smtplib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from news.models import Article
from advertisements.models import Advertisement
from galleries.models import Gallery
from liveblog.models import LiveBlog
from news.models import Category
from videos.models import Video
from webstories.models import WebStory

from .forms import EmailLoginForm, ForgotPasswordForm, OTPVerifyForm, ResetPasswordForm, SignupForm
from .models import LoginOTP, ReporterProfile


User = get_user_model()


def author_detail(request, slug):
    author = get_object_or_404(ReporterProfile, slug=slug, active=True)
    page_obj = Paginator(Article.objects.optimized().published().filter(reporter=author), 20).get_page(request.GET.get("page"))
    return render(request, "accounts/author_detail.html", {"author_profile": author, "page_obj": page_obj})


def _otp_code():
    return f"{random.SystemRandom().randint(100000, 999999)}"


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _otp_throttle_error(request, email, purpose):
    ip = _client_ip(request) or "unknown"
    cooldown_key = f"otp:cooldown:{purpose}:{email}"
    email_key = f"otp:email:{purpose}:{email}"
    ip_key = f"otp:ip:{purpose}:{ip}"
    if cache.get(cooldown_key):
        return "Please wait before requesting another OTP."
    if int(cache.get(email_key) or 0) >= 5:
        return "Too many OTP requests for this email. Please try again later."
    if int(cache.get(ip_key) or 0) >= 20:
        return "Too many OTP requests from this network. Please try again later."
    cache.set(cooldown_key, True, 60)
    cache.set(email_key, int(cache.get(email_key) or 0) + 1, 60 * 60)
    cache.set(ip_key, int(cache.get(ip_key) or 0) + 1, 60 * 60)
    return ""


def _create_otp(request, email, purpose, user=None, full_name=""):
    LoginOTP.objects.filter(email=email, purpose=purpose, used=False).update(used=True)
    otp = LoginOTP.objects.create(
        email=email,
        purpose=purpose,
        user=user,
        full_name=full_name,
        code=_otp_code(),
        ip_address=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:300]),
        expires_at=timezone.now() + timezone.timedelta(minutes=10),
    )
    subject = "Your Desh Darpan Samvad verification code"
    text_message = f"Your OTP is {otp.code}. It is valid for 10 minutes."
    html_message = render_to_string("erp/auth/email_otp.html", {"otp": otp, "purpose": purpose})
    try:
        send_mail(subject, text_message, settings.EMAIL_HOST_USER, [email], html_message=html_message, fail_silently=False)
    except smtplib.SMTPAuthenticationError:
        otp.used = True
        otp.delivery_error = "SMTP authentication failed."
        otp.save(update_fields=["used", "delivery_error"])
        return otp, "SMTP authentication failed. Please check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD."
    except Exception as error:
        otp.used = True
        otp.delivery_error = str(error)
        otp.save(update_fields=["used", "delivery_error"])
        return otp, f"Email could not be sent: {error}"
    otp.delivered = True
    otp.save(update_fields=["delivered"])
    return otp, ""


def _pending_auth(request):
    otp_id = request.session.get("pending_otp_id")
    if not otp_id:
        return None
    return LoginOTP.objects.filter(pk=otp_id, used=False).first()


def portal_login(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = EmailLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).order_by("id").first()
        throttle_error = _otp_throttle_error(request, email, LoginOTP.Purpose.LOGIN)
        if throttle_error:
            messages.error(request, throttle_error)
            return render(request, "erp/auth/login.html", {"form": form, "page_title": "Portal Sign In"})
        otp, email_error = _create_otp(request, email, LoginOTP.Purpose.LOGIN, user=user)
        if email_error:
            messages.error(request, email_error)
            return render(request, "erp/auth/login.html", {"form": form, "page_title": "Portal Sign In"})
        request.session["pending_otp_id"] = otp.pk
        messages.success(request, "OTP sent to your email.")
        return redirect("accounts:verify_otp")
    return render(request, "erp/auth/login.html", {"form": form, "page_title": "Portal Sign In"})


def portal_signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        throttle_error = _otp_throttle_error(request, email, LoginOTP.Purpose.SIGNUP)
        if throttle_error:
            messages.error(request, throttle_error)
            return render(request, "erp/auth/signup.html", {"form": form, "page_title": "Create Portal Account"})
        user = User.objects.create_user(
            username=email,
            email=email,
            password=form.cleaned_data["password"],
            first_name=form.cleaned_data["full_name"],
            is_active=False,
            is_staff=False,
        )
        otp, email_error = _create_otp(request, email, LoginOTP.Purpose.SIGNUP, user=user, full_name=form.cleaned_data["full_name"])
        if email_error:
            user.delete()
            messages.error(request, email_error)
            return render(request, "erp/auth/signup.html", {"form": form, "page_title": "Create Portal Account"})
        request.session["pending_otp_id"] = otp.pk
        messages.success(request, "OTP sent to your email.")
        return redirect("accounts:verify_otp")
    return render(request, "erp/auth/signup.html", {"form": form, "page_title": "Create Portal Account"})


def verify_otp(request):
    otp = _pending_auth(request)
    if not otp or not otp.can_verify():
        messages.error(request, "OTP expired. Please request a new code.")
        return redirect("accounts:login")
    form = OTPVerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        otp.attempts += 1
        if form.cleaned_data["code"] != otp.code:
            otp.save(update_fields=["attempts"])
            form.add_error("code", "Invalid OTP.")
        else:
            otp.used = True
            otp.verified_at = timezone.now()
            otp.save(update_fields=["used", "attempts", "verified_at"])
            request.session.pop("pending_otp_id", None)
            if otp.purpose == LoginOTP.Purpose.SIGNUP:
                user = get_object_or_404(User, pk=otp.user_id)
                user.is_active = True
                user.save(update_fields=["is_active"])
                guest_group = Group.objects.filter(name="Guest").first()
                if guest_group:
                    user.groups.add(guest_group)
                login(request, user)
            elif otp.purpose == LoginOTP.Purpose.PASSWORD_RESET:
                request.session["password_reset_user_id"] = otp.user_id
                return redirect("accounts:reset_password")
            else:
                if not otp.user:
                    messages.error(request, "No active account found for this OTP.")
                    return redirect("accounts:login")
                login(request, otp.user)
            return redirect("accounts:dashboard")
    return render(request, "erp/auth/verify_otp.html", {"form": form, "otp": otp, "page_title": "Verify OTP"})


def forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.filter(email__iexact=form.cleaned_data["email"], is_active=True).order_by("id").first()
        throttle_error = _otp_throttle_error(request, user.email, LoginOTP.Purpose.PASSWORD_RESET)
        if throttle_error:
            messages.error(request, throttle_error)
            return render(request, "erp/auth/forgot_password.html", {"form": form, "page_title": "Forgot Password"})
        otp, email_error = _create_otp(request, user.email, LoginOTP.Purpose.PASSWORD_RESET, user=user)
        if email_error:
            messages.error(request, email_error)
            return render(request, "erp/auth/forgot_password.html", {"form": form, "page_title": "Forgot Password"})
        request.session["pending_otp_id"] = otp.pk
        messages.success(request, "Password reset OTP sent to your email.")
        return redirect("accounts:verify_otp")
    return render(request, "erp/auth/forgot_password.html", {"form": form, "page_title": "Forgot Password"})


def reset_password(request):
    user_id = request.session.get("password_reset_user_id")
    if not user_id:
        return redirect("accounts:forgot_password")
    user = get_object_or_404(User, pk=user_id, is_active=True)
    form = ResetPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["password"])
        user.save(update_fields=["password"])
        request.session.pop("password_reset_user_id", None)
        messages.success(request, "Password updated. Please sign in with OTP.")
        return redirect("accounts:login")
    return render(request, "erp/auth/reset_password.html", {"form": form, "page_title": "Reset Password"})


def portal_logout(request):
    logout(request)
    return redirect("accounts:login")


PORTAL_MODULES = {
    "articles": {"title": "Articles", "permission": "news.view_article", "model": Article, "fields": ["title", "status", "updated_at"]},
    "stories": {"title": "Web Stories", "permission": "webstories.view_webstory", "model": WebStory, "fields": ["title", "active", "published_at"]},
    "videos": {"title": "Videos", "permission": "videos.view_video", "model": Video, "fields": ["title", "active"]},
    "galleries": {"title": "Photo Gallery", "permission": "galleries.view_gallery", "model": Gallery, "fields": ["title", "active"]},
    "advertisements": {"title": "Advertisements", "permission": "advertisements.view_advertisement", "model": Advertisement, "fields": ["name", "placement", "active"]},
    "liveblogs": {"title": "Live Blogs", "permission": "liveblog.view_liveblog", "model": LiveBlog, "fields": ["title", "active"]},
    "categories": {"title": "Categories", "permission": "news.view_category", "model": Category, "fields": ["name", "hindi_name", "active"]},
    "users": {"title": "Users & Roles", "permission": "auth.view_user", "model": User, "fields": ["username", "email", "is_active"]},
}


def _portal_modules_for(user):
    modules = [
        {"key": "articles", "group": "Content", "title": "Articles", "icon": "bi-newspaper", "enabled": user.has_perm("news.change_article") or user.is_superuser},
        {"key": "stories", "group": "Content", "title": "Web Stories", "icon": "bi-phone", "enabled": user.has_perm("webstories.change_webstory") or user.is_superuser},
        {"key": "liveblogs", "group": "Content", "title": "Live Blogs", "icon": "bi-broadcast-pin", "enabled": user.has_perm("liveblog.change_liveblog") or user.is_superuser},
        {"key": "videos", "group": "Media", "title": "Videos", "icon": "bi-play-btn", "enabled": user.has_perm("videos.change_video") or user.is_superuser},
        {"key": "galleries", "group": "Media", "title": "Photo Gallery", "icon": "bi-images", "enabled": user.has_perm("galleries.change_gallery") or user.is_superuser},
        {"key": "advertisements", "group": "Revenue", "title": "Advertisements", "icon": "bi-badge-ad", "enabled": user.has_perm("advertisements.change_advertisement") or user.is_superuser},
        {"key": "categories", "group": "System", "title": "Categories", "icon": "bi-diagram-3", "enabled": user.has_perm("news.change_category") or user.is_superuser},
        {"key": "users", "group": "Access", "title": "Users & Roles", "icon": "bi-people", "enabled": user.has_perm("auth.change_user") or user.is_superuser},
    ]
    for module in modules:
        module["url"] = f"/accounts/portal/{module['key']}/"
    role_names = [group.name for group in user.groups.all()]
    if user.is_superuser:
        role_names.insert(0, "Super Admin")
    elif not role_names:
        role_names.append("Guest")
    return {"modules": modules, "role_names": role_names}


@login_required
def portal_module(request, module):
    config = PORTAL_MODULES.get(module)
    if not config:
        return redirect("accounts:dashboard")
    if not request.user.has_perm(config["permission"]) and not request.user.is_superuser:
        messages.error(request, "You do not have access to this module.")
        return redirect("accounts:dashboard")
    objects = config["model"].objects.all()[:50]
    return render(
        request,
        "erp/module_list.html",
        {"module": module, "config": config, "objects": objects, "page_title": config["title"], **_portal_modules_for(request.user)},
    )


@login_required
def portal_module_new(request, module):
    config = PORTAL_MODULES.get(module)
    if not config:
        return redirect("accounts:dashboard")
    messages.info(request, f"{config['title']} editor will open here. Form builder is the next step.")
    return redirect("accounts:portal_module", module=module)
