from django.urls import path

from . import views

app_name = "galleries"

urlpatterns = [
    path("photos/", views.gallery_list, name="list"),
    path("photos/<int:pk>/<slug:slug>/", views.gallery_detail, name="detail"),
    path("photos/<str:slug>/", views.legacy_gallery_detail, name="legacy_detail"),
]
