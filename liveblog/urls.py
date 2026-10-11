from django.urls import path

from . import views

app_name = "liveblog"

urlpatterns = [
    path("live/", views.live_list, name="list"),
    path("live/<int:pk>/<slug:slug>/", views.live_detail, name="detail"),
    path("live/<str:slug>/", views.legacy_live_detail, name="legacy_detail"),
]
