import logging
import random
import smtplib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from news.models import Article
from advertisements.models import Advertisement
from galleries.models import Gallery
from liveblog.models import LiveBlog
from news.models import Category
from videos.models import Video
from webstories.models import WebStory

from core.models import SiteSettings
from core.throttling import check_rate_limit, client_ip, consume_rate_limit, peek_rate_limit

from .forms import EmailLoginForm, ForgotPasswordForm, OTPVerifyForm, ResetPasswordForm, SignupForm
from .models import LoginOTP, ReporterProfile

logger = logging.getLogger(__name__)


User = get_user_model()

# OTP abuse limits. Named here rather than inline so the security policy is
# reviewable in one place.
OTP_COOLDOWN_SECONDS = 60
OTP_MAX_PER_EMAIL_PER_HOUR = 5
OTP_MAX_PER_IP_PER_HOUR = 20

# Password login limits. These count *failed* attempts only, and expire on their
# own window, so a legitimate user is never locked out indefinitely.
LOGIN_FAILURE_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES_PER_EMAIL = 5
LOGIN_MAX_FAILURES_PER_IP = 20

# Shown whenever an email/password/OTP combination cannot be accepted. Kept
# identical across "no such account" and "wrong credential" so neither the login
# nor the reset flow can be used to discover which addresses are registered.
GENERIC_CREDENTIAL_ERROR = "Invalid email or password."
GENERIC_OTP_SENT_MESSAGE = "If that email is registered, a code has been sent."
GENERIC_OTP_INVALID_ERROR = "Invalid or expired code. Please request a new one."

# Set when an OTP was requested for an address with no account. No code is
# created or emailed, but the flow continues identically so the response cannot
# be used to tell registered addresses from unregistered ones.
DECOY_SESSION_KEY = "pending_otp_decoy"
PENDING_EMAIL_SESSION_KEY = "pending_otp_email"


def author_detail(request, slug):
    author = get_object_or_404(ReporterProfile, slug=slug, active=True)
    page_obj = Paginator(Article.objects.optimized().published().filter(reporter=author), 20).get_page(request.GET.get("page"))
    return render(request, "accounts/author_detail.html", {
        "author_profile": author, "page_obj": page_obj,
        "seo_title": f"{author.display_name} - लेखक प्रोफ़ाइल",
    })


def team(request):
    reporters = ReporterProfile.objects.filter(active=True).select_related("city")
    return render(request, "accounts/team.html", {
        "reporters": reporters, "page_title": "हमारी टीम", "seo_title": "हमारी टीम",
    })


def _otp_code():
    return f"{random.SystemRandom().randint(100000, 999999)}"


def _client_ip(request):
    # Rightmost X-Forwarded-For entry is the hop appended by our own trusted
    # proxy; the leftmost value is client-supplied and can be spoofed. Returns
    # None rather than a placeholder so LoginOTP.ip_address stays a valid inet.
    return client_ip(request)


def _otp_throttle_error(request, email, purpose):
    ip = _client_ip(request) or "unknown"
    return check_rate_limit(
        "otp",
        rules=[
            (f"email:{purpose}:{email}", OTP_MAX_PER_EMAIL_PER_HOUR, 60 * 60,
             "Too many OTP requests for this email. Please try again later."),
            (f"ip:{purpose}:{ip}", OTP_MAX_PER_IP_PER_HOUR, 60 * 60,
             "Too many OTP requests from this network. Please try again later."),
        ],
        cooldown=(f"cooldown:{purpose}:{email}", OTP_COOLDOWN_SECONDS,
                  "Please wait before requesting another OTP."),
    )


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
    html_message = render_to_string("erp/auth/email_otp.html", {"otp": otp, "purpose": purpose, "site_settings": SiteSettings.load()})
    try:
        send_mail(subject, text_message, settings.EMAIL_HOST_USER, [email], html_message=html_message, fail_silently=False)
    except smtplib.SMTPAuthenticationError:
        otp.used = True
        otp.delivery_error = "SMTP authentication failed."
        otp.save(update_fields=["used", "delivery_error"])
        logger.error("OTP email SMTP authentication failed for %s", email)
        return otp, "We could not send the code right now. Please try again shortly."
    except Exception as error:
        otp.used = True
        otp.delivery_error = str(error)
        otp.save(update_fields=["used", "delivery_error"])
        logger.error("OTP email delivery failed for %s: %s", email, error, exc_info=True)
        return otp, "We could not send the code right now. Please try again shortly."
    otp.delivered = True
    otp.save(update_fields=["delivered"])
    return otp, ""


def _pending_auth(request):
    otp_id = request.session.get("pending_otp_id")
    if not otp_id:
        return None
    return LoginOTP.objects.filter(pk=otp_id, used=False).first()


def _login_failure_rules(email, ip):
    return [
        (f"email:{email}", LOGIN_MAX_FAILURES_PER_EMAIL, LOGIN_FAILURE_WINDOW_SECONDS,
         "Too many failed sign-in attempts for this account. Please try again later."),
        (f"ip:{ip}", LOGIN_MAX_FAILURES_PER_IP, LOGIN_FAILURE_WINDOW_SECONDS,
         "Too many failed sign-in attempts from this network. Please try again later."),
    ]


def _start_otp_flow(request, email, purpose, user, full_name=""):
    """Begin an OTP challenge, returning an error message or "".

    When no account matches, nothing is created and no mail is sent, but the
    session is marked so the caller can return the same response it would for a
    real account.
    """
    if user is None:
        request.session.pop("pending_otp_id", None)
        request.session[DECOY_SESSION_KEY] = True
        request.session[PENDING_EMAIL_SESSION_KEY] = email
        return ""
    otp, email_error = _create_otp(request, email, purpose, user=user, full_name=full_name)
    if email_error:
        return email_error
    request.session.pop(DECOY_SESSION_KEY, None)
    request.session["pending_otp_id"] = otp.pk
    request.session[PENDING_EMAIL_SESSION_KEY] = email
    return ""


def portal_login(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = EmailLoginForm(request.POST or None)
    context = {"form": form, "page_title": "Portal Sign In"}
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data.get("password")
        user = User.objects.filter(email__iexact=email, is_active=True).order_by("id").first()

        if password:
            context["login_password_attempted"] = True
            ip = _client_ip(request) or "unknown"
            rules = _login_failure_rules(email, ip)
            # Checked before authenticating and consumed only on failure, so a
            # correct password is never rejected because of earlier typos.
            throttle_error = peek_rate_limit("login", rules)
            if throttle_error:
                messages.error(request, throttle_error)
                return render(request, "erp/auth/login.html", context)

            authenticated_user = authenticate(request, username=user.username, password=password) if user else None
            if not authenticated_user:
                consume_rate_limit("login", rules)
                form.add_error(None, GENERIC_CREDENTIAL_ERROR)
                return render(request, "erp/auth/login.html", context)
            login(request, authenticated_user)
            return redirect("accounts:dashboard")

        throttle_error = _otp_throttle_error(request, email, LoginOTP.Purpose.LOGIN)
        if throttle_error:
            messages.error(request, throttle_error)
            return render(request, "erp/auth/login.html", context)
        email_error = _start_otp_flow(request, email, LoginOTP.Purpose.LOGIN, user)
        if email_error:
            messages.error(request, email_error)
            return render(request, "erp/auth/login.html", context)
        messages.success(request, GENERIC_OTP_SENT_MESSAGE)
        return redirect("accounts:verify_otp")
    return render(request, "erp/auth/login.html", context)


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
    pending_email = request.session.get(PENDING_EMAIL_SESSION_KEY, "")

    # No account matched the requested address. Render the same screen and
    # reject every code, so this path is indistinguishable from a real one.
    if otp is None and request.session.get(DECOY_SESSION_KEY):
        form = OTPVerifyForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            form.add_error("code", GENERIC_OTP_INVALID_ERROR)
        return render(request, "erp/auth/verify_otp.html",
                      {"form": form, "otp": None, "otp_email": pending_email, "page_title": "Verify OTP"})

    if not otp or not otp.can_verify():
        messages.error(request, GENERIC_OTP_INVALID_ERROR)
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
                    messages.error(request, GENERIC_OTP_INVALID_ERROR)
                    return redirect("accounts:login")
                login(request, otp.user)
            return redirect("accounts:dashboard")
    return render(request, "erp/auth/verify_otp.html",
                  {"form": form, "otp": otp, "otp_email": otp.email, "page_title": "Verify OTP"})


def forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)
    context = {"form": form, "page_title": "Forgot Password"}
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).order_by("id").first()
        throttle_error = _otp_throttle_error(request, email, LoginOTP.Purpose.PASSWORD_RESET)
        if throttle_error:
            messages.error(request, throttle_error)
            return render(request, "erp/auth/forgot_password.html", context)
        email_error = _start_otp_flow(request, email, LoginOTP.Purpose.PASSWORD_RESET, user)
        if email_error:
            messages.error(request, email_error)
            return render(request, "erp/auth/forgot_password.html", context)
        messages.success(request, GENERIC_OTP_SENT_MESSAGE)
        return redirect("accounts:verify_otp")
    return render(request, "erp/auth/forgot_password.html", context)


def _flush_other_sessions(user):
    """Delete every stored session belonging to this user.

    A password reset is what a compromised user does to lock an attacker out;
    without this the attacker's existing session survives the reset and the
    action fails at its main purpose.
    """
    user_id = str(user.pk)
    for session in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        if session.get_decoded().get("_auth_user_id") == user_id:
            session.delete()


def reset_password(request):
    user_id = request.session.get("password_reset_user_id")
    if not user_id:
        return redirect("accounts:forgot_password")
    user = get_object_or_404(User, pk=user_id, is_active=True)
    form = ResetPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["password"])
        user.save(update_fields=["password"])
        _flush_other_sessions(user)
        # The reset session itself was just deleted above; start a clean one so
        # no reset state survives into the next sign-in.
        request.session.flush()
        messages.success(request, "Password updated. Please sign in.")
        return redirect("accounts:login")
    return render(request, "erp/auth/reset_password.html", {"form": form, "page_title": "Reset Password"})


def portal_logout(request):
    logout(request)
    return redirect("accounts:login")


PORTAL_MODULES = {
    "articles": {
        "title": "Articles", "permission": "news.view_article", "model": Article, "fields": ["title", "status", "updated_at"],
        "form_fields": [
            "title", "short_title", "summary", "body", "category", "subcategory", "state", "district", "city",
            "featured_image", "image_caption", "image_credit", "seo_title", "meta_description", "keywords", "tags",
            "status", "editor_remarks", "is_breaking", "is_featured", "is_top_story", "is_homepage_hero",
        ],
    },
    "stories": {
        "title": "Web Stories", "permission": "webstories.view_webstory", "model": WebStory, "fields": ["title", "active", "published_at"],
        "form_fields": ["title", "slug", "cover", "category", "published_at", "active", "seo_title", "meta_description"],
    },
    "videos": {
        "title": "Videos", "permission": "videos.view_video", "model": Video, "fields": ["title", "active"],
        "form_fields": ["title", "slug", "thumbnail", "youtube_url", "category", "location", "description", "published_at", "featured", "active", "seo_title", "meta_description"],
    },
    "galleries": {
        "title": "Photo Gallery", "permission": "galleries.view_gallery", "model": Gallery, "fields": ["title", "active"],
        "form_fields": ["title", "slug", "description", "category", "location", "cover_image", "published_at", "active", "seo_title", "meta_description"],
    },
    "advertisements": {
        "title": "Advertisements", "permission": "advertisements.view_advertisement", "model": Advertisement, "fields": ["name", "placement", "active"],
        # html_code is intentionally excluded here — raw-HTML ads stay superuser-only via Django admin
        # (advertisements/admin.py AdvertisementAdminForm.clean_html_code) to avoid reopening the stored-XSS
        # risk flagged in the earlier security review.
        "form_fields": ["name", "ad_type", "image", "desktop_image", "mobile_image", "target_url", "placement", "start_date", "end_date", "active", "priority"],
    },
    "liveblogs": {
        "title": "Live Blogs", "permission": "liveblog.view_liveblog", "model": LiveBlog, "fields": ["title", "active"],
        "form_fields": ["title", "slug", "description", "featured_image", "youtube_live_url", "status", "start_time", "end_time", "category", "location", "active"],
    },
    "categories": {
        "title": "Categories", "permission": "news.view_category", "model": Category, "fields": ["name", "hindi_name", "active"],
        "form_fields": ["name", "hindi_name", "slug", "parent", "description", "icon", "display_order", "show_in_menu", "show_on_homepage", "active", "seo_title", "meta_description"],
    },
    # "users" intentionally has no form_fields — creating/editing User records through a generic
    # ModelForm would store passwords in plain text and bypass is_staff/is_superuser safeguards.
    # User management stays list-only here; real account changes go through Django admin.
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


def _portal_module_or_404(module):
    config = PORTAL_MODULES.get(module)
    if not config:
        return None
    return config


def _require_module_permission(request, config, action="view"):
    permission = config["permission"].replace(".view_", f".{action}_")
    return request.user.has_perm(permission) or request.user.is_superuser


@login_required
def portal_module(request, module):
    config = _portal_module_or_404(module)
    if not config:
        return redirect("accounts:dashboard")
    if not _require_module_permission(request, config, "view"):
        messages.error(request, "You do not have access to this module.")
        return redirect("accounts:dashboard")

    queryset = config["model"].objects.all()
    query = request.GET.get("q", "").strip()
    if query:
        search_field = config["fields"][0]
        try:
            queryset = queryset.filter(**{f"{search_field}__icontains": query})
        except Exception:
            pass

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "erp/module_list.html",
        {
            "module": module,
            "config": config,
            "objects": page_obj,
            "page_obj": page_obj,
            "query": query,
            "can_edit": bool(config.get("form_fields")) and _require_module_permission(request, config, "change"),
            "page_title": config["title"],
            **_portal_modules_for(request.user),
        },
    )


@login_required
def portal_module_new(request, module):
    config = _portal_module_or_404(module)
    if not config or not config.get("form_fields"):
        return redirect("accounts:dashboard")
    if not _require_module_permission(request, config, "add"):
        messages.error(request, "You do not have access to this module.")
        return redirect("accounts:dashboard")

    form_class = modelform_factory(config["model"], fields=config["form_fields"])
    if request.method == "POST":
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            if config["model"] is Article and not obj.author_id:
                obj.author = request.user
            obj.save()
            form.save_m2m()
            messages.success(request, f"{config['title']} created successfully.")
            return redirect("accounts:portal_module", module=module)
    else:
        form = form_class()
    return render(
        request,
        "erp/module_form.html",
        {"module": module, "config": config, "form": form, "is_new": True, "page_title": f"New {config['title']}", **_portal_modules_for(request.user)},
    )


@login_required
def portal_module_edit(request, module, pk):
    config = _portal_module_or_404(module)
    if not config or not config.get("form_fields"):
        return redirect("accounts:dashboard")
    if not _require_module_permission(request, config, "change"):
        messages.error(request, "You do not have access to this module.")
        return redirect("accounts:dashboard")

    instance = get_object_or_404(config["model"], pk=pk)
    form_class = modelform_factory(config["model"], fields=config["form_fields"])
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config['title']} updated successfully.")
            return redirect("accounts:portal_module", module=module)
    else:
        form = form_class(instance=instance)
    return render(
        request,
        "erp/module_form.html",
        {"module": module, "config": config, "form": form, "instance": instance, "is_new": False, "page_title": f"Edit {config['title']}", **_portal_modules_for(request.user)},
    )


@require_POST
@login_required
def portal_module_delete(request, module, pk):
    config = _portal_module_or_404(module)
    if not config or not config.get("form_fields"):
        return redirect("accounts:dashboard")
    if not _require_module_permission(request, config, "delete"):
        messages.error(request, "You do not have access to this module.")
        return redirect("accounts:dashboard")

    instance = get_object_or_404(config["model"], pk=pk)
    # The portal never destroys rows. Articles carry editorial history, bookmarks
    # and PROTECTed author/category links, so they are archived via status; every
    # other module deactivates. A model supporting neither is refused rather than
    # hard-deleted, so adding one to PORTAL_MODULES can never silently start
    # destroying data.
    if isinstance(instance, Article):
        instance.status = Article.Status.ARCHIVED
        instance.save(update_fields=["status"])
        messages.success(request, f"{config['title']} archived.")
    elif hasattr(instance, "active"):
        instance.active = False
        instance.save(update_fields=["active"])
        messages.success(request, f"{config['title']} deactivated.")
    else:
        messages.error(request, f"{config['title']} cannot be removed from the portal. Use Django admin.")
    return redirect("accounts:portal_module", module=module)
