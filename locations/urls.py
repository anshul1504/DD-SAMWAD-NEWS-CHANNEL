from django.urls import path

from . import views

app_name = "locations"

urlpatterns = [
    path("state/<str:state_slug>/", views.state_detail, name="state"),
    path("state/<str:state_slug>/<str:district_slug>/", views.district_detail, name="district"),
    path("state/<str:state_slug>/<str:district_slug>/<str:city_slug>/", views.city_detail, name="city"),
]
