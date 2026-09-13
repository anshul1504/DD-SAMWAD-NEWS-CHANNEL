from django.urls import path

from . import views

app_name = "core"


def _page(route, name, title, key, intro):
    return path(
        route,
        views.static_page,
        {"template": "static_page.html", "title": title, "page_key": key, "intro": intro},
        name=name,
    )


urlpatterns = [
    path("newsletter/", views.newsletter_subscribe, name="newsletter"),
    path("contact/", views.contact, name="contact"),
    path("news-tip/", views.news_tip, name="news_tip"),
    _page("about/", "about", "About Us", "about",
          "देश दर्पण संवाद एक हिंदी-प्रथम डिजिटल समाचार मंच है।"),
    _page("privacy-policy/", "privacy", "Privacy Policy", "privacy",
          "हम कौन-सी जानकारी लेते हैं, क्यों लेते हैं और आपके पास क्या अधिकार हैं।"),
    _page("terms/", "terms", "Terms & Conditions", "terms",
          "इस वेबसाइट के उपयोग की शर्तें।"),
    _page("disclaimer/", "disclaimer", "Disclaimer", "disclaimer",
          "सामग्री की सीमाओं और जिम्मेदारी के बारे में जरूरी जानकारी।"),
    _page("editorial-policy/", "editorial_policy", "Editorial Policy", "editorial_policy",
          "हम खबरें कैसे चुनते, जांचते और प्रकाशित करते हैं।"),
    _page("grievance/", "grievance", "Grievance / Contact", "grievance",
          "शिकायत दर्ज कराने और उसके समाधान की प्रक्रिया।"),
    path("advertise/", views.advertise, name="advertise"),
    path("sponsorship/", views.sponsorship, name="sponsorship"),
    path("investors/", views.investors, name="investors"),
    path("careers/", views.careers, name="careers"),
    path("careers/<slug:slug>/", views.job_detail, name="job_detail"),
    path("epaper/", views.epaper, name="epaper"),
    path("epaper/<str:edition_date>/", views.epaper, name="epaper_date"),
    path("translate/", views.translate_text, name="translate"),
]
