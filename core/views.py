import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import connections
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import CareerApplicationForm, ContactForm, NewsletterForm
from .models import EPaperEdition, JobOpening, NewsletterSubscriber, SiteSettings
from .throttling import check_rate_limit, client_ip

logger = logging.getLogger(__name__)

# Contact form abuse limits. Each accepted submission sends two emails.
CONTACT_COOLDOWN_SECONDS = 60
CONTACT_MAX_PER_EMAIL_PER_HOUR = 3
CONTACT_MAX_PER_IP_PER_HOUR = 5

ALLOWED_TRANSLATE_TARGETS = {
    "hi", "en", "bn", "gu", "as", "or", "kn", "ml", "mr", "ne", "pa", "sa",
    "sd", "ta", "te", "ur", "bho", "mai", "doi", "gom", "ks", "mni-Mtei",
}
TRANSLATE_MAX_TEXTS = 120
TRANSLATE_RATE_LIMIT = 200  # requests per minute per IP
TRANSLATE_CACHE_SECONDS = 60 * 60 * 24
# Short TTL for a failed lookup (both providers unavailable for this text) so
# it gets retried again soon, instead of being stuck "untranslated" for a day.
TRANSLATE_FAILURE_CACHE_SECONDS = 90
# A page with lots of unique strings (homepage headlines, labels, ...) used to
# fire dozens of back-to-back calls at MyMemory/Google with zero pacing,
# which trips their anonymous per-second limits within the first handful of
# calls -- so most of a text-heavy page silently stayed untranslated on its
# first-ever view. A small gap between calls lets far more of them succeed.
TRANSLATE_PROVIDER_DELAY_SECONDS = 0.12
# Keyed per-provider in the shared cache (not a local variable) so the pacing
# holds across concurrent requests/threads/users too -- two people switching
# language at the same moment must not each independently burst the same
# external API right past the per-process delay above.
GOOGLE_TRANSLATE_LAST_CALL_KEY = "translate:google:last_call"
MYMEMORY_TRANSLATE_LAST_CALL_KEY = "translate:mymemory:last_call"


def _pace_provider_call(last_call_key):
    """Block until at least TRANSLATE_PROVIDER_DELAY_SECONDS has passed since
    the last call to this provider from ANY request, then claim the slot.
    Uses wall-clock time.time() (not monotonic()) because the cache is shared
    across worker processes in production, which don't share a monotonic
    clock epoch."""
    now = time.time()
    last_call = cache.get(last_call_key)
    if last_call is not None:
        wait = TRANSLATE_PROVIDER_DELAY_SECONDS - (now - last_call)
        if wait > 0:
            time.sleep(wait)
    cache.set(last_call_key, time.time(), TRANSLATE_PROVIDER_DELAY_SECONDS + 5)


# The free translate APIs mangle short, ambiguous nav/category labels
# (e.g. "खेल" -> "Game" instead of "Sports"). These are fixed site vocabulary,
# so a static override is both more accurate and skips the network call.
TRANSLATE_OVERRIDES = {
    "en": {
        "देश": "National",
        "विदेश": "International",
        "राजनीति": "Politics",
        "बिजनेस": "Business",
        "खेल": "Sports",
        "मनोरंजन": "Entertainment",
        "टेक्नोलॉजी": "Technology",
        "लाइफस्टाइल": "Lifestyle",
        "शिक्षा": "Education",
        "नौकरी": "Jobs",
        "अपराध": "Crime",
        "धर्म": "Religion",
        "ट्रेंडिंग": "Trending",
        "ताजा खबरें": "Latest News",
        "होम": "Home",
        "मीडिया": "Media",
        "अधिक": "More",
        "लोकल": "Local",
        "ब्रेकिंग खबरें": "Breaking News",
        "आज की तेज झलकियां": "Today's Quick Highlights",
        "अभी की बड़ी खबरें": "Top Breaking Stories",
        "ताजा और भरोसेमंद खबरों के लिए तैयार": "Ready for fresh, reliable news",
        "यहां मुख्य खबरें CMS से प्रकाशित होते ही दिखाई देंगी।": "Top stories will appear here as soon as they're published.",
        "24hr stories उपलब्ध नहीं हैं।": "24hr stories are not available.",
        "Breaking news उपलब्ध नहीं है।": "Breaking news is not available.",
        "Latest news उपलब्ध नहीं है।": "Latest news is not available.",
        "Featured news उपलब्ध नहीं है।": "Featured news is not available.",
        "Trending news उपलब्ध नहीं है।": "Trending news is not available.",
        "Most read उपलब्ध नहीं है।": "Most read is not available.",
        "Video news उपलब्ध नहीं है।": "Video news is not available.",
        "Photo gallery उपलब्ध नहीं है।": "Photo gallery is not available.",
        "Web stories उपलब्ध नहीं हैं।": "Web stories are not available.",
        "Opinion stories उपलब्ध नहीं हैं।": "Opinion stories are not available.",
        "Recommended stories उपलब्ध नहीं हैं।": "Recommended stories are not available.",
        "मुख्य सामग्री पर जाएं": "Skip to main content",
        "लाइव": "Live",
        "खोज करें": "Search",
        "लाइव अपडेट": "Live Update",
        "न्यूज टिप": "News Tip",
        "वीडियो": "Video",
        "फोटो": "Photo",
        "वेब स्टोरी": "Web Story",
        "लाइव ब्लॉग": "Live Blog",
        "देश-दुनिया की ताजा खबरें पढ़ें": "Read the latest news from India and the world",
        "मेनू": "Menu",
        "फोटो गैलरी": "Photo Gallery",
        "इंदौर": "Indore",
        "भोपाल": "Bhopal",
        "उज्जैन": "Ujjain",
        "जबलपुर": "Jabalpur",
        "न्यूजलेटर": "Newsletter",
        "विज्ञापन दें": "Advertise",
        "संपर्क": "Contact",
        "विश्वसनीय हिंदी समाचार, स्थानीय अपडेट और डिजिटल मीडिया कवरेज।": "Trusted Hindi news, local updates and digital media coverage.",
        "स्पॉन्सरशिप": "Sponsorship",
        "न्यूज टिप भेजें": "Send a News Tip",
        "हमारे बारे में": "About Us",
        "हमारी टीम": "Our Team",
        "करियर": "Careers",
        "इन्वेस्टर रिलेशंस": "Investor Relations",
        "प्राइवेसी पॉलिसी": "Privacy Policy",
        "नियम और शर्तें": "Terms & Conditions",
        "डिस्क्लेमर": "Disclaimer",
        "एडिटोरियल पॉलिसी": "Editorial Policy",
        "शिकायत / संपर्क": "Grievance / Contact",
        "नई अपडेट": "New Updates",
        "सबसे चर्चित": "Most Talked About",
        "देखें रिपोर्ट": "Watch Report",
        "स्वाइप फॉर्मेट": "Swipe Format",
    },
}

# Google's unofficial endpoint starts returning 429 once our shared egress IP
# gets flagged; once that happens further immediate retries just draw more
# 429s. Back off for a while and go straight to the fallback provider.
GOOGLE_TRANSLATE_COOLDOWN_KEY = "translate:google:cooldown"
GOOGLE_TRANSLATE_COOLDOWN_SECONDS = 10 * 60
MYMEMORY_TRANSLATE_COOLDOWN_KEY = "translate:mymemory:cooldown"
MYMEMORY_TRANSLATE_COOLDOWN_SECONDS = 10 * 60


def _google_translate(text, target):
    google_target = target.split("-", 1)[0]
    query = urllib.parse.urlencode({
        "client": "gtx",
        "sl": "auto",
        "tl": google_target,
        "dt": "t",
        "q": text,
    })
    request = urllib.request.Request(
        f"https://translate.googleapis.com/translate_a/single?{query}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        data = json.loads(response.read(200_000).decode("utf-8"))
    return "".join(part[0] for part in data[0] if part and part[0]).strip() or text


def _mymemory_translate(text, target):
    query = urllib.parse.urlencode({"q": text, "langpair": f"hi|{target}"})
    request = urllib.request.Request(
        f"https://api.mymemory.translated.net/get?{query}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        data = json.loads(response.read(100_000).decode("utf-8"))
    return data.get("responseData", {}).get("translatedText") or text


# page_key -> SiteSettings role, so each policy page's sidebar shows the
# inbox that actually reads it rather than the general address for all of them.
_STATIC_PAGE_EMAIL_ROLE = {
    "grievance": "grievance",
    "editorial_policy": "editorial",
    "privacy": "privacy",
}


def static_page(request, template, title, page_key=None, intro=""):
    """Render an editorial/legal information page.

    Each page has its own content partial under templates/pages/. They used to
    share one generic paragraph, which meant seven separately-linked pages all
    said the same thing.
    """
    site_settings = SiteSettings.load()
    role = _STATIC_PAGE_EMAIL_ROLE.get(page_key)
    contact_email = site_settings.routed_email(role) if role else site_settings.email
    return render(request, template, {
        "page_title": title,
        "seo_title": title,
        "page_key": page_key,
        "page_intro": intro,
        "content_template": f"pages/{page_key}.html" if page_key else None,
        "contact_email": contact_email,
    })


def _send_contact_emails(contact_message, recipient_role="email"):
    site_settings = SiteSettings.load()
    email_context = {"contact_message": contact_message, "site_settings": site_settings, "site_url": settings.SITE_URL}

    admin_recipient = (
        site_settings.routed_email(recipient_role) if recipient_role != "email" else site_settings.email
    ) or settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(
            subject=f"नया संपर्क संदेश: {contact_message.subject}",
            message=f"{contact_message.name} ({contact_message.email}) ने संदेश भेजा है:\n\n{contact_message.message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_recipient],
            html_message=render_to_string("emails/contact_admin_notification.html", email_context),
            fail_silently=False,
        )
    except Exception:
        logger.error("Failed to send contact admin notification email", exc_info=True)

    try:
        send_mail(
            subject="आपका संदेश प्राप्त हो गया है — Desh Darpan Samvad",
            message=(
                f"धन्यवाद {contact_message.name} जी, आपका संदेश हमें प्राप्त हो गया है। "
                "हमारी टीम जल्द ही आपसे संपर्क करेगी।"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact_message.email],
            html_message=render_to_string("emails/contact_user_confirmation.html", email_context),
            fail_silently=False,
        )
    except Exception:
        logger.error("Failed to send contact confirmation email to %s", contact_message.email, exc_info=True)
        return False
    return True


def _contact_throttle_error(request, email, scope="contact"):
    """Each accepted submission sends two emails, one to a user-supplied address.
    Without a limit the form is an open mail relay, and the resulting domain
    blacklisting would also stop OTP delivery. Same cache primitive as the OTP
    throttle so both share one mechanism."""
    ip = client_ip(request) or "unknown"
    return check_rate_limit(
        scope,
        rules=[
            (f"email:{email}", CONTACT_MAX_PER_EMAIL_PER_HOUR, 60 * 60,
             "आप इस ईमेल से बहुत सारे संदेश भेज चुके हैं। कृपया कुछ समय बाद प्रयास करें।"),
            (f"ip:{ip}", CONTACT_MAX_PER_IP_PER_HOUR, 60 * 60,
             "इस नेटवर्क से बहुत सारे संदेश भेजे गए हैं। कृपया कुछ समय बाद प्रयास करें।"),
        ],
        cooldown=(f"cooldown:{ip}", CONTACT_COOLDOWN_SECONDS,
                  "कृपया अगला संदेश भेजने से पहले कुछ क्षण प्रतीक्षा करें।"),
    )


def _contact_form_view(request, template, redirect_name, page_title, subject_prefix="", recipient_role="email"):
    """Shared handler behind /contact/ and /news-tip/: same throttled
    ContactMessage backend, different template, copy and inbox so a news tip
    doesn't look like — or land in the same place as — a generic support
    request."""
    form = ContactForm(request.POST or None)
    context = {"form": form, "page_title": page_title, "seo_title": page_title}
    if request.method == "POST" and form.is_valid():
        throttle_error = _contact_throttle_error(request, form.cleaned_data["email"].strip().lower())
        if throttle_error:
            messages.error(request, throttle_error)
            return render(request, template, context)
        contact_message = form.save(commit=False)
        if subject_prefix and not contact_message.subject.startswith(subject_prefix):
            contact_message.subject = f"{subject_prefix}{contact_message.subject}"
        contact_message.save()
        delivered = _send_contact_emails(contact_message, recipient_role=recipient_role)
        if delivered:
            messages.success(request, "आपका संदेश प्राप्त हो गया है। पुष्टि ईमेल आपके इनबॉक्स में भेज दी गई है।")
        else:
            # The message is saved either way; do not claim an email was sent.
            messages.success(request, "आपका संदेश प्राप्त हो गया है। हमारी टीम जल्द ही आपसे संपर्क करेगी।")
        return redirect(redirect_name)
    return render(request, template, context)


def contact(request):
    return _contact_form_view(request, "contact.html", "core:contact", "Contact Us")


def news_tip(request):
    return _contact_form_view(
        request, "news_tip.html", "core:news_tip", "News Tip",
        subject_prefix="[News Tip] ", recipient_role="tips",
    )


def advertise(request):
    return _contact_form_view(
        request, "advertise.html", "core:advertise", "Advertise With Us",
        subject_prefix="[Advertising] ", recipient_role="advertise",
    )


def sponsorship(request):
    return _contact_form_view(
        request, "sponsorship.html", "core:sponsorship", "Sponsorship",
        subject_prefix="[Sponsorship] ", recipient_role="sponsorship",
    )


def investors(request):
    return _contact_form_view(
        request, "investors.html", "core:investors", "Investor Relations",
        subject_prefix="[Investor Relations] ", recipient_role="investor",
    )


def _send_career_emails(application):
    site_settings = SiteSettings.load()
    email_context = {"application": application, "site_settings": site_settings, "site_url": settings.SITE_URL}
    admin_recipient = site_settings.routed_email("careers") or settings.DEFAULT_FROM_EMAIL
    role = application.job.title if application.job else application.role_applied

    try:
        send_mail(
            subject=f"नया आवेदन: {role}",
            message=f"{application.name} ({application.email}) ने \"{role}\" के लिए आवेदन किया है।",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_recipient],
            html_message=render_to_string("emails/career_admin_notification.html", email_context),
            fail_silently=False,
        )
    except Exception:
        logger.error("Failed to send career application admin notification email", exc_info=True)

    try:
        send_mail(
            subject="आपका आवेदन प्राप्त हो गया है — Desh Darpan Samvad",
            message=(
                f"धन्यवाद {application.name} जी, \"{role}\" के लिए आपका आवेदन हमें प्राप्त हो गया है। "
                "योग्य उम्मीदवारों से हमारी टीम सीधे संपर्क करेगी।"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            html_message=render_to_string("emails/career_applicant_confirmation.html", email_context),
            fail_silently=False,
        )
    except Exception:
        logger.error("Failed to send career application confirmation email to %s", application.email, exc_info=True)
        return False
    return True


def careers(request):
    """Listing only — applying happens on a job's own detail page, with the
    form scoped to that role, never through a picker bolted onto the list."""
    openings = JobOpening.objects.filter(active=True)
    return render(request, "careers.html", {"openings": openings, "page_title": "Careers", "seo_title": "Careers"})


def job_detail(request, slug):
    job = get_object_or_404(JobOpening, slug=slug, active=True)
    form = CareerApplicationForm(request.POST or None, request.FILES or None, job=job)
    context = {"form": form, "job": job, "page_title": job.title, "seo_title": f"{job.title} - Careers"}
    if request.method == "POST" and form.is_valid():
        throttle_error = _contact_throttle_error(request, form.cleaned_data["email"].strip().lower(), scope="career")
        if throttle_error:
            messages.error(request, throttle_error)
            return render(request, "job_detail.html", context)
        application = form.save(commit=False)
        application.job = job
        application.save()
        delivered = _send_career_emails(application)
        if delivered:
            messages.success(request, "आपका आवेदन प्राप्त हो गया है। पुष्टि ईमेल आपके इनबॉक्स में भेज दी गई है।")
        else:
            messages.success(request, "आपका आवेदन प्राप्त हो गया है। हमारी टीम जल्द ही आपसे संपर्क करेगी।")
        return redirect("core:job_detail", slug)
    return render(request, "job_detail.html", context)


def epaper(request, edition_date=None):
    city_slug = request.GET.get("city")
    editions = EPaperEdition.objects.filter(active=True).prefetch_related("pages")
    if city_slug:
        editions = editions.filter(city__slug=city_slug)
    else:
        editions = editions.filter(city__isnull=True)

    current = None
    if edition_date:
        current = editions.filter(edition_date=edition_date).first()
        if not current:
            current = editions.first()
    else:
        current = editions.first()

    # Only cities with a real, active upload appear here -- never a
    # fabricated list of cities that don't actually have an edition.
    latest_per_city = (
        EPaperEdition.objects.filter(active=True, city__isnull=False)
        .values("city")
        .annotate(latest_date=Max("edition_date"))
    )
    local_editions = [
        edition
        for row in latest_per_city
        if (edition := EPaperEdition.objects.filter(
            active=True, city_id=row["city"], edition_date=row["latest_date"]
        ).select_related("city").first())
    ]

    return render(request, "epaper.html", {
        "current": current,
        "recent_editions": editions[:14],
        "local_editions": local_editions,
        "current_city": city_slug,
        "page_title": "ई-पेपर",
        "seo_title": f"ई-पेपर - {current.edition_date}" if current else "ई-पेपर",
        "today": timezone.localdate(),
        "page_images": [p.image.url for p in current.pages.all()] if current else [],
    })


def _safe_referer(request, fallback="home"):
    """Referer is attacker-influenceable: a page on another origin can submit
    here and its URL arrives in the header, so redirecting to it blindly turns
    this endpoint into an open redirect. Only same-host targets are honoured."""
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return referer
    return fallback


def newsletter_subscribe(request):
    if request.method == "POST":
        form = NewsletterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "न्यूजलेटर सब्सक्रिप्शन सफल रहा। धन्यवाद!")
        elif NewsletterSubscriber.objects.filter(
            email__iexact=(request.POST.get("email") or "").strip()
        ).exists():
            # The unique constraint makes a repeat signup "invalid", but telling
            # an already-subscribed reader to "enter a correct email" is wrong.
            messages.info(request, "यह ईमेल पहले से सब्सक्राइब है। धन्यवाद!")
        else:
            messages.error(request, "कृपया सही ईमेल पता दर्ज करें।")
    return redirect(_safe_referer(request))


@csrf_exempt
@require_POST
def translate_text(request):
    ip = client_ip(request, default="unknown")
    rate_key = f"translate:rate:{ip}"
    request_count = cache.get(rate_key) or 0
    if request_count >= TRANSLATE_RATE_LIMIT:
        return JsonResponse({"translations": [], "error": "rate_limited"}, status=429)
    cache.set(rate_key, request_count + 1, 60)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError, UnicodeDecodeError):
        return JsonResponse({"translations": []}, status=400)

    target = payload.get("target") or "hi"
    if target not in ALLOWED_TRANSLATE_TARGETS:
        return JsonResponse({"translations": []}, status=400)

    texts = [str(item).strip()[:500] for item in payload.get("texts", []) if str(item).strip()]
    if target == "hi" or not texts:
        return JsonResponse({"translations": texts})

    translations = []
    for text in texts[:TRANSLATE_MAX_TEXTS]:
        # Python's built-in hash() is randomised per-process (PYTHONHASHSEED),
        # so every server restart produced different cache keys for identical
        # text -- the cache silently never hit, and every page load re-drove
        # full traffic at the free translate APIs. sha1 is stable across runs.
        text_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
        cache_key = f"translate:text:{target}:{text_hash}"
        cached = cache.get(cache_key)
        if cached is not None:
            translations.append(cached)
            continue
        override = TRANSLATE_OVERRIDES.get(target, {}).get(text)
        if override is not None:
            cache.set(cache_key, override, TRANSLATE_CACHE_SECONDS)
            translations.append(override)
            continue
        result = None
        if not cache.get(GOOGLE_TRANSLATE_COOLDOWN_KEY):
            _pace_provider_call(GOOGLE_TRANSLATE_LAST_CALL_KEY)
            try:
                result = _google_translate(text, target)
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    logger.info("Google translation rate-limited; backing off for %ss", GOOGLE_TRANSLATE_COOLDOWN_SECONDS)
                    cache.set(GOOGLE_TRANSLATE_COOLDOWN_KEY, True, GOOGLE_TRANSLATE_COOLDOWN_SECONDS)
                else:
                    logger.warning("Google translation failed for target=%s: %s", target, exc)
            except Exception:
                logger.warning("Google translation failed for target=%s", target, exc_info=True)
        if result is None and not cache.get(MYMEMORY_TRANSLATE_COOLDOWN_KEY):
            _pace_provider_call(MYMEMORY_TRANSLATE_LAST_CALL_KEY)
            try:
                result = _mymemory_translate(text, target)
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    logger.info("MyMemory translation rate-limited; backing off for %ss", MYMEMORY_TRANSLATE_COOLDOWN_SECONDS)
                    cache.set(MYMEMORY_TRANSLATE_COOLDOWN_KEY, True, MYMEMORY_TRANSLATE_COOLDOWN_SECONDS)
                else:
                    logger.warning("MyMemory translation failed for target=%s: %s", target, exc)
            except Exception:
                logger.warning("MyMemory translation failed for target=%s", target, exc_info=True)
        if result is None:
            # Both providers failed (rate-limited/cooling down/network error):
            # fall back to the original text for THIS response, but do not
            # cache the failure for a full day -- that would permanently
            # freeze this exact string as "untranslated" long after the
            # providers recover. A short TTL lets the next request retry soon.
            translations.append(text)
            cache.set(cache_key, text, TRANSLATE_FAILURE_CACHE_SECONDS)
            continue
        cache.set(cache_key, result, TRANSLATE_CACHE_SECONDS)
        translations.append(result)
    return JsonResponse({"translations": translations})


def robots_txt(request):
    return render(request, "robots.txt", content_type="text/plain")


@never_cache
def healthz(request):
    """Liveness/readiness probe for load balancers and uptime monitoring.

    Reports only "ok"/"error" per dependency — never versions, settings or
    connection strings, since this endpoint is typically unauthenticated.
    A failing database returns 503 so a broken instance is pulled from rotation.
    """
    checks = {"database": "ok"}
    healthy = True
    try:
        # Cheapest possible round-trip that proves the connection works.
        connections["default"].cursor().execute("SELECT 1")
    except Exception:
        logger.error("Health check: database unavailable", exc_info=True)
        checks["database"] = "error"
        healthy = False

    return JsonResponse(
        {"status": "ok" if healthy else "error", "checks": checks},
        status=200 if healthy else 503,
    )
