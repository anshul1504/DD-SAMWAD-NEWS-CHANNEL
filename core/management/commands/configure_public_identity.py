from django.core.cache import cache
from django.core.management.base import BaseCommand

from core.models import SiteSettings


class Command(BaseCommand):
    help = "Set the official public contact and social identity idempotently."

    def handle(self, *args, **options):
        settings = SiteSettings.load()
        settings.email = "info@ddsamvad.com"
        settings.instagram_url = "https://www.instagram.com/ddsamvad/"
        settings.facebook_url = "https://www.facebook.com/ddsamvad/"
        settings.twitter_url = "https://x.com/ddsamvad"
        settings.youtube_url = "https://www.youtube.com/@ddsamvadofficial"
        settings.save(update_fields=[
            "email", "instagram_url", "facebook_url", "twitter_url",
            "youtube_url", "updated_at",
        ])
        cache.delete("dds:site_settings")
        self.stdout.write(self.style.SUCCESS("Official public identity configured."))
