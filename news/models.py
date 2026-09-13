import nh3
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify

from accounts.models import ReporterProfile
from core.youtube import youtube_embed_url
from locations.models import City, District, State

ARTICLE_BODY_ALLOWED_TAGS = {
    "p", "br", "strong", "em", "u", "s", "blockquote", "h2", "h3", "h4",
    "ul", "ol", "li", "a", "img", "figure", "figcaption", "table", "thead",
    "tbody", "tr", "th", "td", "hr", "sub", "sup",
}
ARTICLE_BODY_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height", "loading"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}


class Category(models.Model):
    name = models.CharField(max_length=120)
    hindi_name = models.CharField(max_length=120, blank=True)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=60, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    show_in_menu = models.BooleanField(default=True)
    show_on_homepage = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    seo_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.hindi_name or self.name

    def get_absolute_url(self):
        return reverse("news:category", args=[self.slug])


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("news:tag", args=[self.slug])


class ArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Article.Status.PUBLISHED, published_at__lte=timezone.now())

    def breaking(self):
        return self.published().filter(is_breaking=True)

    def featured(self):
        return self.published().filter(is_featured=True)

    def trending(self):
        return self.published().filter(models.Q(is_trending=True) | models.Q(views__gt=0)).order_by("-is_trending", "-views")

    def optimized(self):
        return self.select_related("category", "state", "district", "city", "author", "reporter__user").prefetch_related("tags")


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=240)
    short_title = models.CharField(max_length=140, blank=True)
    slug = models.SlugField(max_length=260, unique=True, allow_unicode=True)
    summary = models.TextField(blank=True)
    body = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="articles")
    subcategory = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="subcategory_articles")
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="articles")
    reporter = models.ForeignKey(ReporterProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    featured_image = models.ImageField(upload_to="articles/%Y/%m/", blank=True)
    image_caption = models.CharField(max_length=220, blank=True)
    image_credit = models.CharField(max_length=120, blank=True)
    video_url = models.URLField(blank=True)
    youtube_url = models.URLField(
        blank=True,
        help_text="कोई भी YouTube लिंक चलेगा — Watch, Shorts, Share (?si=...) या Embed लिंक, जो भी कॉपी करें।",
    )
    seo_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    keywords = models.CharField(max_length=300, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    editor_remarks = models.TextField(blank=True)
    is_breaking = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_top_story = models.BooleanField(default=False, db_index=True)
    is_homepage_hero = models.BooleanField(default=False, db_index=True)
    is_trending = models.BooleanField(default=False, db_index=True)
    is_editor_pick = models.BooleanField(default=False, db_index=True)
    allow_comments = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0, db_index=True)
    reading_time = models.PositiveIntegerField(default=1)
    canonical_url = models.URLField(blank=True)

    objects = ArticleQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["category", "published_at"]),
            models.Index(fields=["city", "published_at"]),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.status == self.Status.PUBLISHED and not all([self.title, self.category_id, self.body, self.author_id, self.published_at]):
            raise ValidationError("Published articles require title, category, body, author and published time.")

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or "news"
            slug = base
            counter = 2
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        if self.body:
            self.body = nh3.clean(
                self.body,
                tags=ARTICLE_BODY_ALLOWED_TAGS,
                attributes=ARTICLE_BODY_ALLOWED_ATTRIBUTES,
                url_schemes={"http", "https", "mailto"},
                link_rel="noopener noreferrer nofollow",
            )
        words = strip_tags(self.body).split()
        self.reading_time = max(1, round(len(words) / 220))
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("news:article_detail", args=[self.slug])

    @property
    def embed_url(self):
        return youtube_embed_url(self.youtube_url) or youtube_embed_url(self.video_url)


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "article")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} saved {self.article}"

# Create your models here.
