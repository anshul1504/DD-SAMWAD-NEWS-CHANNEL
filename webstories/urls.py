from django.urls import path

from . import views

app_name = "webstories"

urlpatterns = [
    path("web-stories/", views.story_list, name="list"),
    path("web-stories/<int:pk>/<slug:slug>/", views.story_detail, name="detail"),
    path("web-stories/<str:slug>/", views.legacy_story_detail, name="legacy_detail"),
]
