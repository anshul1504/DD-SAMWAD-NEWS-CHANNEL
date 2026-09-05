from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Gallery


def gallery_list(request):
    page_obj = Paginator(Gallery.objects.filter(active=True), 20).get_page(request.GET.get("page"))
    return render(request, "galleries/list.html", {"page_obj": page_obj, "page_title": "फोटो गैलरी"})


def gallery_detail(request, slug):
    gallery = get_object_or_404(Gallery.objects.prefetch_related("images"), slug=slug, active=True)
    return render(request, "galleries/detail.html", {"gallery": gallery, "seo_title": gallery.seo_title or gallery.title})
