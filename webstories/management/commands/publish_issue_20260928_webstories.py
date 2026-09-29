import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify

from news.models import Article
from webstories.models import StorySlide, WebStory


class Command(BaseCommand):
    help = "Create fresh web stories from the lead reports in issue 03."

    def handle(self, *args, **options):
        articles = list(Article.objects.published().filter(published_at__date="2026-09-28", featured_image__gt="").order_by("published_at")[:10])
        active_slugs = []
        for position, article in enumerate(articles):
            slug = f"issue-03-{slugify(article.title, allow_unicode=True)[:190]}"
            active_slugs.append(slug)
            story, _ = WebStory.objects.update_or_create(slug=slug, defaults={
                "title": article.title, "cover": article.featured_image.name,
                "category": article.category, "published_at": timezone.now() - timezone.timedelta(minutes=position),
                "active": True, "seo_title": article.title[:180], "meta_description": article.summary[:300],
            })
            text = re.sub(r"\s+", " ", strip_tags(article.body)).strip()
            chunks = [part.strip() for part in re.split(r"(?<=[।!?])\s+", text) if len(part.strip()) > 45][:4]
            if not chunks:
                chunks = [article.summary or article.title]
            story.slides.all().delete()
            article_url = f"{settings.SITE_URL.rstrip('/')}{article.get_absolute_url()}"
            for order, chunk in enumerate(chunks):
                StorySlide.objects.create(
                    story=story, image=article.featured_image.name,
                    heading=article.title if order == 0 else f"मुख्य बिंदु {order + 1}", text=chunk[:420],
                    cta_label="पूरी खबर पढ़ें" if order == len(chunks)-1 else "",
                    cta_url=article_url if order == len(chunks)-1 else "", order=order,
                )
            self.stdout.write(f"Web story {story.pk}: {story.slug}")
        stale_count, _ = WebStory.objects.filter(slug__startswith="issue-03-").exclude(slug__in=active_slugs).delete()
        if stale_count:
            self.stdout.write(f"Removed {stale_count} stale issue story records/slides.")
        self.stdout.write(self.style.SUCCESS(f"Published {len(articles)} issue web stories."))
