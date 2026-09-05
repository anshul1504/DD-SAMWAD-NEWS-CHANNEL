from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import LiveBlog


def live_list(request):
    page_obj = Paginator(LiveBlog.objects.filter(active=True), 20).get_page(request.GET.get("page"))
    return render(request, "liveblog/list.html", {"page_obj": page_obj, "page_title": "लाइव"})


def live_detail(request, slug):
    liveblog = get_object_or_404(LiveBlog.objects.prefetch_related("updates"), slug=slug, active=True)
    return render(request, "liveblog/detail.html", {"liveblog": liveblog, "seo_title": liveblog.title})
