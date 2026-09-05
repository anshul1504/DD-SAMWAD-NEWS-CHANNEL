from django.urls import path

from . import views

app_name = "videos"

urlpatterns = [
    path("videos/", views.video_list, name="list"),
    path("videos/<str:slug>/", views.video_detail, name="detail"),
]
