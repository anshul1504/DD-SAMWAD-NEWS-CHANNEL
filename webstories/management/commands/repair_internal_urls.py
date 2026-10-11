from django.core.management.base import BaseCommand

from webstories.models import StorySlide, canonicalize_internal_article_url


class Command(BaseCommand):
    help = "Replace legacy internal Hindi article URLs in Web Story CTAs with canonical clean URLs."

    def handle(self, *args, **options):
        repaired = 0
        for slide in StorySlide.objects.exclude(cta_url="").iterator():
            canonical = canonicalize_internal_article_url(slide.cta_url)
            if canonical == slide.cta_url:
                continue
            StorySlide.objects.filter(pk=slide.pk).update(cta_url=canonical)
            repaired += 1
        self.stdout.write(self.style.SUCCESS(f"Repaired {repaired} internal Web Story CTA URL(s)."))
