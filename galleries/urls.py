from django.urls import path

from . import views

app_name = "galleries"

urlpatterns = [
    path("photos/", views.gallery_list, name="list"),
    path("photos/<str:slug>/", views.gallery_detail, name="detail"),
]
