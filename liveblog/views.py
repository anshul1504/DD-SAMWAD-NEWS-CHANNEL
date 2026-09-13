from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, When
from django.shortcuts import get_object_or_404, render

from .models import LiveBlog

# Live-in-progress first, then scheduled (coming up), then ended — instead of
# the default -start_time which buries a live blog under an older scheduled one.
_STATUS_ORDER = Case(
    When(status=LiveBlog.Status.LIVE, then=0),
    When(status=LiveBlog.Status.SCHEDULED, then=1),
    default=2,
    output_field=IntegerField(),
)


def live_list(request):
    queryset = LiveBlog.objects.filter(active=True).annotate(status_order=_STATUS_ORDER).order_by("status_order", "-start_time")
    page_obj = Paginator(queryset, 20).get_page(request.GET.get("page"))
    return render(request, "liveblog/list.html", {"page_obj": page_obj, "page_title": "लाइव", "seo_title": "लाइव अपडेट"})


def live_detail(request, slug):
    liveblog = get_object_or_404(LiveBlog.objects.prefetch_related("updates"), slug=slug, active=True)
    return render(request, "liveblog/detail.html", {"liveblog": liveblog, "seo_title": liveblog.title})
