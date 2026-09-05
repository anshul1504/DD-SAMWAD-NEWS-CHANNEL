from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("newsletter/", views.newsletter_subscribe, name="newsletter"),
    path("contact/", views.contact, name="contact"),
    path("about/", views.static_page, {"template": "static_page.html", "title": "About Us"}, name="about"),
    path("privacy-policy/", views.static_page, {"template": "static_page.html", "title": "Privacy Policy"}, name="privacy"),
    path("terms/", views.static_page, {"template": "static_page.html", "title": "Terms & Conditions"}, name="terms"),
    path("disclaimer/", views.static_page, {"template": "static_page.html", "title": "Disclaimer"}, name="disclaimer"),
    path("editorial-policy/", views.static_page, {"template": "static_page.html", "title": "Editorial Policy"}, name="editorial_policy"),
    path("grievance/", views.static_page, {"template": "static_page.html", "title": "Grievance / Contact"}, name="grievance"),
    path("advertise/", views.static_page, {"template": "static_page.html", "title": "Advertise With Us"}, name="advertise"),
    path("translate/", views.translate_text, name="translate"),
]
