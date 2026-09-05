from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from news.models import Article

from .models import City, District, State


def paginate(request, queryset):
    return Paginator(queryset, 20).get_page(request.GET.get("page"))


def state_detail(request, state_slug):
    state = get_object_or_404(State, slug=state_slug, active=True)
    articles = Article.objects.optimized().published().filter(state=state)
    return render(request, "news/listing.html", {"page_title": state.name, "page_obj": paginate(request, articles), "state": state})


def district_detail(request, state_slug, district_slug):
    district = get_object_or_404(District, state__slug=state_slug, slug=district_slug, active=True)
    articles = Article.objects.optimized().published().filter(district=district)
    return render(request, "news/listing.html", {"page_title": district.name, "page_obj": paginate(request, articles), "district": district})


def city_detail(request, state_slug, district_slug, city_slug):
    city = get_object_or_404(City, district__state__slug=state_slug, district__slug=district_slug, slug=city_slug, active=True)
    articles = Article.objects.optimized().published().filter(city=city)
    return render(request, "news/listing.html", {"page_title": city.name, "page_obj": paginate(request, articles), "city": city})
