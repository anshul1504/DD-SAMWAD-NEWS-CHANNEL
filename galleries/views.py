from django.shortcuts import get_object_or_404, redirect, render

from core.utils import paginate
from .models import Gallery


def gallery_list(request):
    page_obj = paginate(request, Gallery.objects.filter(active=True), per_page=20)
    return render(request, "galleries/list.html", {"page_obj": page_obj, "page_title": "फोटो गैलरी", "seo_title": "फोटो गैलरी"})


def gallery_detail(request, pk, slug):
    gallery = get_object_or_404(Gallery.objects.prefetch_related("images"), pk=pk, active=True)
    if slug != gallery.public_url_slug:
        return redirect(gallery.get_absolute_url(), permanent=True)
    return render(request, "galleries/detail.html", {"gallery": gallery, "seo_title": gallery.seo_title or gallery.title})


def legacy_gallery_detail(request, slug):
    gallery = get_object_or_404(Gallery, slug=slug, active=True)
    return redirect(gallery.get_absolute_url(), permanent=True)
