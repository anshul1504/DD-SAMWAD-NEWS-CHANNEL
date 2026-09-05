import json
import urllib.parse
import urllib.request

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ContactForm, NewsletterForm


def static_page(request, template, title):
    return render(request, template, {"page_title": title, "seo_title": title})


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "आपका संदेश प्राप्त हो गया है।")
        return redirect("core:contact")
    return render(request, "contact.html", {"form": form, "page_title": "Contact Us"})


def newsletter_subscribe(request):
    if request.method == "POST":
        form = NewsletterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Newsletter subscription सफल रहा।")
        else:
            messages.error(request, "कृपया सही ईमेल दर्ज करें।")
    return redirect(request.META.get("HTTP_REFERER", "home"))


@require_POST
def translate_text(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError, UnicodeDecodeError):
        return JsonResponse({"translations": []}, status=400)

    target = payload.get("target") or "hi"
    texts = [str(item).strip() for item in payload.get("texts", []) if str(item).strip()]
    if target == "hi" or not texts:
        return JsonResponse({"translations": texts})

    translations = []
    for text in texts[:80]:
        try:
            query = urllib.parse.urlencode({"q": text, "langpair": f"hi|{target}"})
            with urllib.request.urlopen(f"https://api.mymemory.translated.net/get?{query}", timeout=6) as response:
                data = json.loads(response.read().decode("utf-8"))
            translations.append(data.get("responseData", {}).get("translatedText") or text)
        except Exception:
            translations.append(text)
    return JsonResponse({"translations": translations})


def robots_txt(request):
    return render(request, "robots.txt", content_type="text/plain")
