from datetime import date

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from news.models import Article
from webstories.models import StorySlide, WebStory


class Command(BaseCommand):
    help = "Publish clean web stories for the 12 October 2026 print issue."

    def handle(self, *args, **options):
        articles = list(
            Article.objects.published()
            .filter(published_at__date=date(2026, 10, 12), is_homepage_hero=True)
            .exclude(featured_image="")
            .order_by("published_at")
        )
        active_slugs = []
        for position, article in enumerate(articles):
            slug = f"issue-05-{slugify(article.title, allow_unicode=True)[:190]}"
            active_slugs.append(slug)
            story, _ = WebStory.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": article.title, "cover": "",
                    "category": article.category,
                    "published_at": timezone.now() - timezone.timedelta(minutes=position),
                    "active": True, "seo_title": article.title[:180],
                    "meta_description": article.summary[:300],
                },
            )
            # Copy the approved article photo into Web Stories' own media
            # location.  A Story must not depend on an article image URL that
            # can be replaced during a later newspaper import.
            article.featured_image.open("rb")
            image_bytes = article.featured_image.read()
            article.featured_image.close()
            story.cover.save(f"issue-05-{article.pk}-cover.jpg", ContentFile(image_bytes), save=True)
            story.slides.all().delete()
            StorySlide.objects.create(
                story=story, heading=article.title, text=article.summary,
                cta_label="पूरी खबर पढ़ें", cta_url=f"{settings.SITE_URL.rstrip('/')}{article.get_absolute_url()}", order=0,
            )
            slide = story.slides.get(order=0)
            slide.image.save(f"issue-05-{article.pk}-slide.jpg", ContentFile(image_bytes), save=True)
            self.stdout.write(f"Web story: {story.title}")
        WebStory.objects.filter(slug__startswith="issue-05-").exclude(slug__in=active_slugs).delete()
        self.stdout.write(self.style.SUCCESS(f"Published {len(articles)} issue 05 web stories."))
