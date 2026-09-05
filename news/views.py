from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.forms import NewsletterForm
from advertisements.models import Advertisement
from galleries.models import Gallery
from liveblog.models import LiveBlog
from videos.models import Video
from webstories.models import WebStory

from .models import Article, Bookmark, Category, Tag


def paginate(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


def pagination_context(request, queryset, per_page=20):
    params = request.GET.copy()
    params.pop("page", None)
    return {
        "page_obj": paginate(request, queryset, per_page),
        "pagination_query": params.urlencode(),
    }


def home(request):
    articles = Article.objects.optimized().published()
    story_cutoff = timezone.now() - timezone.timedelta(hours=24)
    stories = WebStory.objects.filter(active=True).prefetch_related("slides")
    categories = Category.objects.filter(active=True, show_on_homepage=True).exclude(slug="home")
    home_categories = []
    for cat in categories:
        cat_articles = articles.filter(category=cat)[:5]
        if cat_articles:
            home_categories.append((cat, cat_articles))
        if len(home_categories) == 7:
            break
    context = {
        "hero_articles": articles.filter(is_homepage_hero=True)[:5] or articles[:5],
        "latest_articles": articles[:12],
        "trending_articles": Article.objects.optimized().trending()[:6],
        "top_stories": articles.filter(is_top_story=True)[:6],
        "editor_picks": articles.filter(is_editor_pick=True)[:6],
        "most_read": articles.order_by("-views")[:6],
        "home_categories": home_categories,
        "galleries": Gallery.objects.filter(active=True).prefetch_related("images")[:6],
        "videos": Video.objects.filter(active=True)[:6],
        "webstories": stories[:8],
        "day_stories": stories.filter(published_at__gte=story_cutoff)[:12],
        "liveblogs": LiveBlog.objects.filter(active=True)[:3],
        "newsletter_form": NewsletterForm(),
        "seo_title": "Desh Darpan Samvad - ताजा हिंदी समाचार",
        "meta_description": "देश, प्रदेश, शहर और दुनिया की ताजा हिंदी खबरें।",
    }
    return render(request, "home.html", context)


def article_detail(request, slug):
    article = get_object_or_404(Article.objects.optimized().published(), slug=slug)
    viewed_key = f"viewed_article_{article.pk}"
    if not request.session.get(viewed_key):
        Article.objects.filter(pk=article.pk).update(views=F("views") + 1)
        request.session[viewed_key] = True
        article.views += 1
    related = Article.objects.optimized().published().filter(
        Q(category=article.category) | Q(city=article.city) | Q(tags__in=article.tags.all())
    ).exclude(pk=article.pk).distinct()[:6]
    context = {
        "article": article,
        "related_articles": related,
        "latest_articles": Article.objects.optimized().published().exclude(pk=article.pk)[:6],
        "most_read": Article.objects.optimized().published().exclude(pk=article.pk).order_by("-views")[:6],
        "seo_title": article.seo_title or article.title,
        "meta_description": article.meta_description or article.summary,
        "article_jsonld": {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": article.title,
            "description": article.meta_description or article.summary,
            "datePublished": article.published_at.isoformat(),
            "dateModified": article.updated_at.isoformat(),
            "author": {"@type": "Person", "name": article.reporter.display_name if article.reporter else article.author.get_full_name() or article.author.username},
            "publisher": {"@type": "Organization", "name": "Desh Darpan Samvad"},
            "mainEntityOfPage": request.build_absolute_uri(),
            "image": request.build_absolute_uri(article.featured_image.url) if article.featured_image else "",
        },
    }
    return render(request, "news/article_detail.html", context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, active=True)
    queryset = Article.objects.optimized().published().filter(category=category)
    return render(request, "news/listing.html", {
        "page_title": category.hindi_name or category.name,
        **pagination_context(request, queryset),
        "category": category,
        "seo_title": category.seo_title or category.name,
        "meta_description": category.meta_description or category.description,
    })


def latest(request):
    queryset = Article.objects.optimized().published()
    return render(request, "news/listing.html", {"page_title": "ताजा खबरें", **pagination_context(request, queryset)})


def trending(request):
    queryset = Article.objects.optimized().trending()
    return render(request, "news/listing.html", {"page_title": "ट्रेंडिंग", **pagination_context(request, queryset)})


def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    queryset = tag.articles.optimized().published()
    return render(request, "news/listing.html", {"page_title": f"#{tag.name}", **pagination_context(request, queryset)})


def search(request):
    query = request.GET.get("q", "").strip()
    results = Article.objects.optimized().published()
    if query:
        results = results.filter(
            Q(title__icontains=query) | Q(short_title__icontains=query) | Q(summary__icontains=query) |
            Q(body__icontains=query) | Q(tags__name__icontains=query) | Q(keywords__icontains=query) |
            Q(author__username__icontains=query) | Q(reporter__display_name__icontains=query)
        ).distinct()
    else:
        results = results.none()
    return render(request, "news/search_results.html", {"query": query, "result_count": results.count(), **pagination_context(request, results)})


@login_required
def bookmark_article(request, pk):
    article = get_object_or_404(Article.objects.published(), pk=pk)
    Bookmark.objects.get_or_create(user=request.user, article=article)
    messages.success(request, "खबर सेव कर दी गई है।")
    return redirect(article)


@login_required
def dashboard(request):
    user = request.user
    my_articles = Article.objects.filter(author=user).select_related("category").order_by("-updated_at")
    permissions = {
        "article_add": user.has_perm("news.add_article"),
        "article_change": user.has_perm("news.change_article"),
        "article_publish": user.has_perm("news.change_article") or user.is_superuser,
        "categories": user.has_perm("news.change_category") or user.is_superuser,
        "ads": user.has_perm("advertisements.change_advertisement") or user.is_superuser,
        "gallery": user.has_perm("galleries.change_gallery") or user.is_superuser,
        "video": user.has_perm("videos.change_video") or user.is_superuser,
        "webstories": user.has_perm("webstories.change_webstory") or user.is_superuser,
        "liveblog": user.has_perm("liveblog.change_liveblog") or user.is_superuser,
        "users": user.has_perm("auth.change_user") or user.is_superuser,
    }
    role_names = [group.name for group in user.groups.all()]
    if user.is_superuser:
        role_names.insert(0, "Super Admin")
    elif not role_names:
        role_names.append("Reader")

    modules = [
        {"key": "articles", "group": "Content", "title": "Articles", "label": "News Desk", "icon": "bi-newspaper", "enabled": permissions["article_change"], "count": Article.objects.count()},
        {"key": "stories", "group": "Content", "title": "Web Stories", "label": "Story Studio", "icon": "bi-phone", "enabled": permissions["webstories"], "count": WebStory.objects.filter(active=True).count()},
        {"key": "liveblogs", "group": "Content", "title": "Live Blogs", "label": "Live Desk", "icon": "bi-broadcast-pin", "enabled": permissions["liveblog"], "count": LiveBlog.objects.filter(active=True).count()},
        {"key": "videos", "group": "Media", "title": "Videos", "label": "Media Desk", "icon": "bi-play-btn", "enabled": permissions["video"], "count": Video.objects.filter(active=True).count()},
        {"key": "galleries", "group": "Media", "title": "Photo Gallery", "label": "Visual Desk", "icon": "bi-images", "enabled": permissions["gallery"], "count": Gallery.objects.filter(active=True).count()},
        {"key": "advertisements", "group": "Revenue", "title": "Advertisements", "label": "Revenue", "icon": "bi-badge-ad", "enabled": permissions["ads"], "count": Advertisement.objects.filter(active=True).count()},
        {"key": "categories", "group": "System", "title": "Categories", "label": "Taxonomy", "icon": "bi-diagram-3", "enabled": permissions["categories"], "count": Category.objects.filter(active=True).count()},
        {"key": "users", "group": "Access", "title": "Users & Roles", "label": "Access", "icon": "bi-people", "enabled": permissions["users"], "count": User.objects.filter(is_active=True).count()},
    ]
    for module in modules:
        module["url"] = f"/accounts/portal/{module['key']}/"
        module["add_url"] = f"/accounts/portal/{module['key']}/new/"

    context = {
        "my_articles": my_articles[:20],
        "draft_count": my_articles.filter(status=Article.Status.DRAFT).count(),
        "submitted_count": my_articles.filter(status=Article.Status.SUBMITTED).count(),
        "published_count": my_articles.filter(status=Article.Status.PUBLISHED).count(),
        "review_count": Article.objects.filter(status__in=[Article.Status.SUBMITTED, Article.Status.UNDER_REVIEW]).count(),
        "total_published": Article.objects.published().count(),
        "total_articles": Article.objects.count(),
        "active_ads": Advertisement.objects.filter(active=True).count(),
        "active_stories": WebStory.objects.filter(active=True).count(),
        "active_videos": Video.objects.filter(active=True).count(),
        "active_galleries": Gallery.objects.filter(active=True).count(),
        "active_liveblogs": LiveBlog.objects.filter(active=True).count(),
        "role_names": role_names,
        "is_guest_user": "Guest" in role_names,
        "permissions": permissions,
        "modules": modules,
        "review_queue": Article.objects.filter(status__in=[Article.Status.SUBMITTED, Article.Status.UNDER_REVIEW]).select_related("category", "author")[:8],
        "recent_articles": Article.objects.select_related("category", "author").order_by("-updated_at")[:8],
    }
    return render(request, "accounts/dashboard.html", context)
