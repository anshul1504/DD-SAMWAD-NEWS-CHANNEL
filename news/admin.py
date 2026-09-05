from django.contrib import admin

from .models import Article, Bookmark, Category, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "hindi_name", "parent", "display_order", "show_in_menu", "show_on_homepage", "active")
    list_filter = ("active", "show_in_menu", "show_on_homepage")
    search_fields = ("name", "hindi_name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.action(description="Publish selected articles")
def publish_articles(modeladmin, request, queryset):
    queryset.update(status=Article.Status.PUBLISHED)


@admin.action(description="Mark as breaking")
def mark_breaking(modeladmin, request, queryset):
    queryset.update(is_breaking=True)


@admin.action(description="Remove breaking flag")
def remove_breaking(modeladmin, request, queryset):
    queryset.update(is_breaking=False)


@admin.action(description="Mark as featured")
def mark_featured(modeladmin, request, queryset):
    queryset.update(is_featured=True)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "city", "status", "published_at", "views", "is_featured", "is_breaking")
    list_filter = ("category", "status", "author", "state", "city", "is_breaking", "is_featured", "published_at")
    search_fields = ("title", "short_title", "slug", "summary", "author__username", "reporter__display_name")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "subcategory", "state", "district", "city", "author", "reporter", "tags")
    filter_horizontal = ("tags",)
    actions = (publish_articles, mark_breaking, remove_breaking, mark_featured)
    fieldsets = (
        ("Content", {"fields": ("title", "short_title", "slug", "summary", "body")}),
        ("Classification", {"fields": ("category", "subcategory", "tags")}),
        ("Location", {"fields": ("state", "district", "city")}),
        ("Media", {"fields": ("featured_image", "image_caption", "image_credit", "video_url", "youtube_url")}),
        ("Publishing", {"fields": ("author", "reporter", "status", "published_at", "editor_remarks", "allow_comments")}),
        ("SEO", {"fields": ("seo_title", "meta_description", "keywords", "canonical_url")}),
        ("Homepage Placement", {"fields": ("is_breaking", "is_featured", "is_top_story", "is_homepage_hero", "is_trending", "is_editor_pick")}),
        ("Analytics", {"fields": ("views", "reading_time")}),
    )
    readonly_fields = ("reading_time",)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "article", "created_at")
    search_fields = ("user__username", "article__title")

# Register your models here.
