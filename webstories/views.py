from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import WebStory


def story_list(request):
    page_obj = Paginator(WebStory.objects.filter(active=True), 20).get_page(request.GET.get("page"))
    return render(request, "webstories/list.html", {"page_obj": page_obj, "page_title": "वेब स्टोरीज"})


def story_detail(request, slug):
    story = get_object_or_404(WebStory.objects.prefetch_related("slides"), slug=slug, active=True)
    return render(request, "webstories/detail.html", {"story": story, "seo_title": story.seo_title or story.title})
