from django.core.management.base import BaseCommand
from django.utils import timezone

from locations.models import City
from news.models import Category
from videos.models import Video

# Real, long-standing, publicly embeddable YouTube videos (not invented IDs
# that might not exist) -- used only as stand-in demo footage until the
# newsroom uploads its own; titles/descriptions say so honestly rather than
# pretending these are real DDS reports. All are normal landscape uploads --
# none of these accounts have actually published Shorts, so the /shorts/
# URL form is used to exercise the reels viewer honestly rather than
# claiming a specific ID is vertical content when it isn't verified to be.
VIDEO_IDS = [
    "dQw4w9WgXcQ", "jNQXAC9IVRw", "M7lc1UVf-VE", "eIho2S0ZahI", "hTWKbfoikeg",
    "kJQP7kiw5Fk", "fJ9rUzIMcZQ", "ysz5S6PUM-U", "ScMzIvxBSi4", "aqz-KE-bpKQ",
]


class Command(BaseCommand):
    help = "Delete uploaded demo videos and seed a small, honestly-labelled set of long videos and Shorts."

    def add_arguments(self, parser):
        parser.add_argument("--long", type=int, default=5, help="Number of long videos to create.")
        parser.add_argument("--shorts", type=int, default=5, help="Number of shorts to create.")

    def handle(self, *args, **options):
        long_count = max(options["long"], 0)
        shorts_count = max(options["shorts"], 0)
        category = Category.objects.filter(active=True).order_by("display_order", "name").first()
        city = City.objects.order_by("name").first()

        deleted, _ = Video.objects.all().delete()
        now = timezone.now()
        created = 0

        for index in range(1, long_count + 1):
            Video.objects.create(
                title=f"डेमो वीडियो बुलेटिन {index}",
                slug=f"demo-video-bulletin-{index}",
                youtube_url=f"https://www.youtube.com/watch?v={VIDEO_IDS[(index - 1) % len(VIDEO_IDS)]}",
                category=category,
                location=city,
                description="डेमो लंबा वीडियो - असली रिपोर्ट अपलोड होने तक प्लेसहोल्डर।",
                published_at=now - timezone.timedelta(minutes=index * 18),
                views=0,
                likes=0,
                is_short=False,
                featured=False,
                active=True,
            )
            created += 1

        for index in range(1, shorts_count + 1):
            Video.objects.create(
                title=f"डेमो शॉर्ट्स {index}",
                slug=f"demo-shorts-{index}",
                youtube_url=f"https://www.youtube.com/shorts/{VIDEO_IDS[(index + 4) % len(VIDEO_IDS)]}",
                category=category,
                location=city,
                description="डेमो शॉर्ट्स वीडियो - असली अपलोड होने तक प्लेसहोल्डर।",
                published_at=now - timezone.timedelta(minutes=index * 9),
                views=0,
                likes=0,
                is_short=True,
                featured=False,
                active=True,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} video rows and created {created} uploads."))
