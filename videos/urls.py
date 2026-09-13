from django.urls import path

from . import views

app_name = "videos"

urlpatterns = [
    path("videos/", views.video_list, name="list"),
    path("shorts/", views.shorts_list, name="shorts"),
    path("videos/<str:slug>/", views.video_detail, name="detail"),
    path("videos/<str:slug>/comments/", views.video_comments, name="comments"),
    path("videos/<str:slug>/comments/new/", views.video_comment_create, name="comment_create"),
    path("videos/<str:slug>/like/", views.video_like_toggle, name="like_toggle"),
    path("videos/<str:slug>/view/", views.video_view_increment, name="view_increment"),
]
