from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from news.models import Category
from webstories.models import StorySlide, WebStory


class Command(BaseCommand):
    help = "Seed 30 demo web stories for the homepage story carousel."

    def handle(self, *args, **options):
        category = Category.objects.filter(show_on_homepage=True).first() or Category.objects.first()
        image_dir = Path(settings.MEDIA_ROOT) / "demo-home"
        image_names = [
            "premium-newsroom-hero.png",
            "real-city-news.png",
            "real-market-news.png",
            "real-sports-news.png",
            "news-1.jpg",
            "news-2.jpg",
            "news-3.jpg",
            "news-4.jpg",
            "news-5.jpg",
            "news-6.jpg",
            "news-7.jpg",
            "news-8.jpg",
            "news-9.jpg",
            "news-10.jpg",
        ]
        images = [f"demo-home/{name}" for name in image_names if (image_dir / name).exists()]
        fallback = images[0] if images else ""

        topics = [
            "सुबह की बड़ी खबरें",
            "शहर का ताजा अपडेट",
            "राजनीति की तेज हलचल",
            "बाजार की बड़ी बात",
            "खेल जगत की खबर",
            "टेक्नोलॉजी अपडेट",
            "मनोरंजन की झलक",
            "एजुकेशन अलर्ट",
            "करियर और जॉब अपडेट",
            "क्राइम रिपोर्ट",
        ]

        created = 0
        for index in range(30):
            title = f"{topics[index % len(topics)]} {index + 1}"
            story, was_created = WebStory.objects.update_or_create(
                slug=f"portal-story-{index + 1}",
                defaults={
                    "title": title,
                    "cover": images[index % len(images)] if images else fallback,
                    "category": category,
                    "published_at": timezone.now() - timezone.timedelta(minutes=index * 18),
                    "active": True,
                    "seo_title": title,
                    "meta_description": "तेज, साफ और विजुअल फॉर्मेट में जरूरी खबरें।",
                },
            )
            created += int(was_created)
            for slide_index in range(4):
                StorySlide.objects.update_or_create(
                    story=story,
                    order=slide_index,
                    defaults={
                        "image": images[(index + slide_index) % len(images)] if images else fallback,
                        "heading": f"{title}: अपडेट {slide_index + 1}",
                        "text": "यह स्टोरी स्लाइड मुख्य जानकारी को छोटे और आसान विजुअल फॉर्मेट में दिखाती है।",
                    },
                )

        self.stdout.write(self.style.SUCCESS(f"30 homepage stories ready. New stories created: {created}"))
