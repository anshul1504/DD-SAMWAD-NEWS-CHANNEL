from datetime import date

from core.models import EPaperEdition
from galleries.models import Gallery
from news.models import Article
from webstories.models import WebStory


issue_date = date(2026, 10, 5)
articles = Article.objects.filter(published_at__date=issue_date).order_by("published_at", "pk")
edition = EPaperEdition.objects.get(edition_date=issue_date, city=None)
gallery = Gallery.objects.get(slug="desh-darpan-issue-04-5-october-2026")
stories = WebStory.objects.filter(slug__startswith="issue-04-", active=True)
bad_tokens = ("à¤", "ï¿½", "�", "विस्तृत मूल रिपोर्ट")

checks = {
    "articles": articles.count(),
    "empty_bodies": articles.filter(body="").count(),
    "images": articles.exclude(featured_image="").count(),
    "headings": sum("<h2>" in article.body for article in articles),
    "named_bylines": articles.exclude(reporter=None).count(),
    "breaking": articles.filter(is_breaking=True).count(),
    "heroes": articles.filter(is_homepage_hero=True).count(),
    "epaper_pages": edition.pages.count(),
    "gallery_images": gallery.images.count(),
    "webstories": stories.count(),
    "story_slides": sum(story.slides.count() for story in stories),
    "bad_text_hits": sum(
        any(token in f"{article.title} {article.summary} {article.body}" for token in bad_tokens)
        for article in articles
    ),
}
print(checks)

expected = {
    "articles": 27, "empty_bodies": 0, "images": 22, "headings": 27,
    "named_bylines": 12, "breaking": 6, "heroes": 5,
    "epaper_pages": 8, "gallery_images": 22, "webstories": 10,
    "bad_text_hits": 0,
}
for key, value in expected.items():
    if checks[key] != value:
        raise SystemExit(f"{key}: expected {value}, got {checks[key]}")
print("ISSUE_04_VERIFICATION=PASS")
