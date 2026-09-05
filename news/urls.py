from django.urls import path

from . import views

app_name = "news"

urlpatterns = [
    path("latest/", views.latest, name="latest"),
    path("trending/", views.trending, name="trending"),
    path("search/", views.search, name="search"),
    path("category/<str:slug>/", views.category_detail, name="category"),
    path("tag/<str:slug>/", views.tag_detail, name="tag"),
    path("news/<str:slug>/", views.article_detail, name="article_detail"),
    path("bookmark/<int:pk>/", views.bookmark_article, name="bookmark"),
]
