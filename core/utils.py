from django.core.paginator import Paginator


def paginate(request, queryset, per_page=20):
    """Shared pagination helper -- every listing page across the apps
    (news, videos, webstories, galleries, liveblog) paginated the same
    Paginator(...).get_page(request.GET.get("page")) call independently."""
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))
