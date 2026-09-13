import hashlib
import json

from django.conf import settings
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from core.throttling import check_rate_limit, client_ip
from core.utils import paginate
from .forms import VideoCommentForm
from .models import Video, VideoLike, youtube_embed_url

COMMENT_RATE_LIMIT = 6  # per IP per 10 minutes -- a live comment box is a small, fast form, easy to script-spam otherwise.
COMMENT_COOLDOWN_SECONDS = 8
LIKE_RATE_LIMIT = 20  # per IP per 10 minutes -- generous since toggling is a single tap, not a form.
VIEW_RATE_LIMIT = 90  # per IP per 10 minutes -- enough for swiping, not enough for view inflation scripts.


def _ip_hash(request):
    ip = client_ip(request, default="unknown")
    # Hashed, not stored raw, since VideoLike rows are otherwise unbounded and
    # kept indefinitely (there's no reason to retain a plaintext IP that long).
    return hashlib.sha1(f"{settings.SECRET_KEY}:{ip}".encode()).hexdigest()


def _video_archive(request, *, shorts=False):
    from news.models import Category  # local import: avoids a videos<->news import-order issue at app load

    base_queryset = (
        Video.objects.filter(active=True)
        .select_related("category")
        .annotate(comment_count=Count("comments", filter=Q(comments__approved=True)))
        .order_by("-published_at")
    )
    queryset = base_queryset.filter(is_short=shorts)

    category_slug = request.GET.get("category")
    active_category = None
    if category_slug:
        active_category = Category.objects.filter(slug=category_slug, active=True).first()
        if active_category:
            queryset = queryset.filter(category=active_category)

    filter_categories = (
        Category.objects.filter(active=True, video__active=True, video__is_short=shorts)
        .distinct()
        .order_by("display_order", "name")
    )

    page_obj = paginate(request, queryset, per_page=24 if shorts else 15)
    page_title = "Shorts" if shorts else "Video News"
    seo_title = f"{active_category} {page_title}" if active_category else page_title
    return render(request, "videos/list.html", {
        "page_obj": page_obj,
        "page_title": page_title,
        "seo_title": seo_title,
        "filter_categories": filter_categories,
        "active_category": active_category,
        "total_count": queryset.count(),
        "featured_videos": Video.objects.filter(active=True, is_short=shorts, featured=True)[:5],
        "most_watched": Video.objects.filter(active=True, is_short=shorts).order_by("-views")[:5],
        "is_shorts_page": shorts,
    })


def video_list(request):
    return _video_archive(request, shorts=False)


def shorts_list(request):
    return _video_archive(request, shorts=True)

def video_detail(request, slug):
    video = get_object_or_404(Video, slug=slug, active=True)
    Video.objects.filter(pk=video.pk).update(views=F("views") + 1)
    video.views += 1

    # A reels/shorts-style swipe feed needs the whole playlist client-side so
    # swiping to the next video is instant (swap the iframe src) instead of a
    # full page reload. Plain dicts only -- embed_url is a computed property,
    # not a DB field, so the model instances themselves can't go through
    # json_script directly.
    queue = list(
        Video.objects.filter(active=True, is_short=video.is_short)
        .annotate(comment_count=Count("comments", filter=Q(comments__approved=True)))
        .order_by("-published_at")
        .values("slug", "title", "description", "youtube_url", "views", "likes", "comment_count")[:60]
    )
    if not any(item["slug"] == slug for item in queue):
        queue.insert(0, {
            "slug": video.slug, "title": video.title, "description": video.description,
            "youtube_url": video.youtube_url, "views": video.views, "likes": video.likes,
            "comment_count": video.comments.filter(approved=True).count(),
        })

    visitor_hash = _ip_hash(request)
    liked_slugs = set(
        VideoLike.objects.filter(ip_hash=visitor_hash, video__slug__in=[item["slug"] for item in queue])
        .values_list("video__slug", flat=True)
    )

    feed = []
    start_index = 0
    for item in queue:
        embed = youtube_embed_url(item["youtube_url"])
        if not embed:
            continue
        if item["slug"] == slug:
            start_index = len(feed)
            item["views"] = video.views
        feed.append({
            "slug": item["slug"],
            "title": item["title"],
            "description": item["description"],
            "embed_url": embed,
            "views": item["views"],
            "likes": item["likes"],
            "liked": item["slug"] in liked_slugs,
            "comment_count": item["comment_count"],
            "url": reverse("videos:detail", args=[item["slug"]]),
            "comments_url": reverse("videos:comments", args=[item["slug"]]),
            "comment_create_url": reverse("videos:comment_create", args=[item["slug"]]),
            "like_url": reverse("videos:like_toggle", args=[item["slug"]]),
            "view_url": reverse("videos:view_increment", args=[item["slug"]]),
        })

    return render(request, "videos/detail.html", {
        "video": video,
        "seo_title": video.seo_title or video.title,
        "feed_json": feed,
        "start_index": start_index,
    })


def _serialize_comment(comment):
    return {
        "name": comment.name,
        "text": comment.text,
        "created_at": comment.created_at.strftime("%d %b, %H:%M"),
    }


@require_GET
def video_comments(request, slug):
    video = get_object_or_404(Video, slug=slug, active=True)
    comments = video.comments.filter(approved=True)[:200]
    return JsonResponse({"comments": [_serialize_comment(c) for c in comments]})


@require_POST
def video_comment_create(request, slug):
    video = get_object_or_404(Video, slug=slug, active=True)
    ip = client_ip(request, default="unknown")
    throttle_error = check_rate_limit(
        "video_comment",
        rules=[(f"ip:{ip}", COMMENT_RATE_LIMIT, 10 * 60, "आप बहुत तेज़ी से कमेंट भेज रहे हैं। कृपया कुछ देर बाद कोशिश करें।")],
        cooldown=(f"cooldown:{ip}", COMMENT_COOLDOWN_SECONDS, "कृपया अगला कमेंट भेजने से पहले कुछ क्षण रुकें।"),
    )
    if throttle_error:
        return JsonResponse({"error": throttle_error}, status=429)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid submission."}, status=400)

    form = VideoCommentForm(payload)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return JsonResponse({"error": first_error}, status=400)

    comment = form.save(commit=False)
    comment.video = video
    comment.save()
    return JsonResponse({"comment": _serialize_comment(comment), "comment_count": video.comments.filter(approved=True).count()})


@require_POST
def video_like_toggle(request, slug):
    video = get_object_or_404(Video, slug=slug, active=True)
    ip = client_ip(request, default="unknown")
    throttle_error = check_rate_limit(
        "video_like",
        rules=[(f"ip:{ip}", LIKE_RATE_LIMIT, 10 * 60, "आप बहुत तेज़ी से लाइक कर रहे हैं। कृपया कुछ देर बाद कोशिश करें।")],
    )
    if throttle_error:
        return JsonResponse({"error": throttle_error}, status=429)

    visitor_hash = _ip_hash(request)
    existing = VideoLike.objects.filter(video=video, ip_hash=visitor_hash).first()
    if existing:
        existing.delete()
        Video.objects.filter(pk=video.pk).update(likes=F("likes") - 1)
        liked = False
    else:
        VideoLike.objects.create(video=video, ip_hash=visitor_hash)
        Video.objects.filter(pk=video.pk).update(likes=F("likes") + 1)
        liked = True

    video.refresh_from_db(fields=["likes"])
    return JsonResponse({"liked": liked, "likes": video.likes})


@require_POST
def video_view_increment(request, slug):
    video = get_object_or_404(Video, slug=slug, active=True)
    ip = client_ip(request, default="unknown")
    throttle_error = check_rate_limit(
        "video_view",
        rules=[(f"ip:{ip}", VIEW_RATE_LIMIT, 10 * 60, "बहुत तेज़ी से वीडियो देखे जा रहे हैं।")],
        cooldown=(f"video:{video.pk}:ip:{ip}", 30, "यह व्यू अभी गिना जा चुका है।"),
    )
    if throttle_error:
        return JsonResponse({"views": video.views, "error": throttle_error}, status=429)
    Video.objects.filter(pk=video.pk).update(views=F("views") + 1)
    video.refresh_from_db(fields=["views"])
    return JsonResponse({"views": video.views})
