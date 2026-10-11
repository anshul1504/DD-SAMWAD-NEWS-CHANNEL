from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.utils import paginate
from news.models import Category
from .models import WebStory


def story_list(request):
    queryset = (
        WebStory.objects.filter(active=True, published_at__lte=timezone.now(), slides__isnull=False)
        .select_related("category")
        .distinct()
        .order_by("-published_at")
    )

    category_slug = request.GET.get("category")
    active_category = None
    if category_slug:
        active_category = Category.objects.filter(slug=category_slug, active=True).first()
        if active_category:
            queryset = queryset.filter(category=active_category)

    # Only offer categories that actually have a story right now, so the
    # filter row never dead-ends on an empty result.
    filter_categories = (
        Category.objects.filter(
            active=True,
            webstory__active=True,
            webstory__published_at__lte=timezone.now(),
            webstory__slides__isnull=False,
        )
        .distinct()
        .order_by("display_order", "name")
    )

    page_obj = paginate(request, queryset, per_page=20)
    seo_title = f"{active_category} की वेब स्टोरीज" if active_category else "वेब स्टोरीज"
    return render(request, "webstories/list.html", {
        "page_obj": page_obj,
        "page_title": "वेब स्टोरीज",
        "seo_title": seo_title,
        "filter_categories": filter_categories,
        "active_category": active_category,
        "total_count": queryset.count(),
    })


def story_detail(request, pk, slug):
    story = get_object_or_404(
        WebStory.objects.filter(
            active=True,
            published_at__lte=timezone.now(),
            slides__isnull=False,
        ).prefetch_related("slides").distinct(),
        pk=pk,
    )
    if slug != story.public_url_slug:
        return redirect(story.get_absolute_url(), permanent=True)
    return render(request, "webstories/detail.html", {"story": story, "seo_title": story.seo_title or story.title})


def legacy_story_detail(request, slug):
    story = get_object_or_404(
        WebStory.objects.filter(active=True, published_at__lte=timezone.now(), slides__isnull=False).distinct(),
        slug=slug,
    )
    return redirect(story.get_absolute_url(), permanent=True)
