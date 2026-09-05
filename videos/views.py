from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, render

from .models import Video


def video_list(request):
    page_obj = Paginator(Video.objects.filter(active=True), 20).get_page(request.GET.get("page"))
    return render(request, "videos/list.html", {"page_obj": page_obj, "page_title": "वीडियो"})


def video_detail(request, slug):
    video = get_object_or_404(Video, slug=slug, active=True)
    Video.objects.filter(pk=video.pk).update(views=F("views") + 1)
    video.views += 1
    return render(request, "videos/detail.html", {"video": video, "seo_title": video.seo_title or video.title})
