from pathlib import Path
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from galleries.models import Gallery
from locations.models import City, District, State
from news.models import Article, Category
from videos.models import Video
from webstories.models import StorySlide, WebStory


class Command(BaseCommand):
    help = "Seed polished homepage demo content with local editorial images."

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        image_dir = media_root / "demo-home"
        image_dir.mkdir(parents=True, exist_ok=True)

        font_bold = self._font(42)
        font_small = self._font(22)
        palette = [
            ("#071024", "#0b3474", "Politics"),
            ("#14213d", "#e31e28", "Breaking"),
            ("#083344", "#0e7490", "City"),
            ("#111827", "#16a34a", "Business"),
            ("#1e1b4b", "#7c3aed", "Technology"),
            ("#3b0a17", "#e11d48", "Sports"),
            ("#0f172a", "#f59e0b", "Culture"),
            ("#052e16", "#22c55e", "Education"),
            ("#172554", "#38bdf8", "World"),
            ("#312e81", "#ec4899", "Lifestyle"),
        ]
        image_paths = []
        for index, (start, end, label) in enumerate(palette, start=1):
            rel_path = f"demo-home/news-{index}.jpg"
            path = media_root / rel_path
            if not path.exists():
                self._make_image(path, start, end, label, font_bold, font_small)
            image_paths.append(rel_path)

        author, _ = User.objects.get_or_create(
            username="dds_editor",
            defaults={"first_name": "Desk", "last_name": "Editor", "email": "editor@deshdarpansamvad.in", "is_staff": True},
        )
        editor_password = os.getenv("DEMO_EDITOR_PASSWORD") or get_random_string(14)
        author.set_password(editor_password)
        author.save()

        state, _ = State.objects.get_or_create(name="मध्य प्रदेश", slug="madhya-pradesh")
        district, _ = District.objects.get_or_create(state=state, name="इंदौर", slug="indore")
        city, _ = City.objects.get_or_create(district=district, name="इंदौर", slug="indore")

        category_names = [
            ("national", "National", "देश"),
            ("international", "International", "विदेश"),
            ("politics", "Politics", "राजनीति"),
            ("business", "Business", "बिजनेस"),
            ("sports", "Sports", "खेल"),
            ("entertainment", "Entertainment", "मनोरंजन"),
            ("technology", "Technology", "टेक्नोलॉजी"),
            ("lifestyle", "Lifestyle", "लाइफस्टाइल"),
            ("education", "Education", "शिक्षा"),
            ("jobs-career", "Jobs/Career", "नौकरी"),
            ("crime", "Crime", "अपराध"),
            ("religion", "Religion/Spirituality", "धर्म"),
        ]
        categories = []
        for order, (slug, name, hindi) in enumerate(category_names, start=1):
            cat, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "hindi_name": hindi, "display_order": order, "show_in_menu": True, "show_on_homepage": True},
            )
            categories.append(cat)

        headlines = [
            "इंदौर में स्मार्ट ट्रैफिक सिस्टम से लोगों को बड़ी राहत",
            "दिल्ली से आई बड़ी अपडेट, नई नीति पर तेज चर्चा",
            "वैश्विक बाजारों के संकेत से निवेशकों की नजरें कारोबार पर",
            "भारतीय टीम ने रोमांचक मुकाबले में शानदार जीत दर्ज की",
            "नई टेक्नोलॉजी से स्कूलों में डिजिटल पढ़ाई को मिलेगी रफ्तार",
            "युवाओं के लिए रोजगार मेले में हजारों पदों पर आवेदन शुरू",
            "शहर में सुरक्षा व्यवस्था मजबूत, संवेदनशील क्षेत्रों में निगरानी",
            "त्योहारों से पहले बाजारों में रौनक, कारोबारियों में उत्साह",
            "अंतरराष्ट्रीय मंच पर भारत की पहल को मिला समर्थन",
            "स्वास्थ्य और लाइफस्टाइल पर विशेषज्ञों ने दिए जरूरी सुझाव",
            "धार्मिक स्थलों पर विशेष व्यवस्था, श्रद्धालुओं के लिए नई सुविधा",
            "एडिटोरियल: स्थानीय पत्रकारिता की विश्वसनीयता क्यों जरूरी है",
        ]
        body = (
            "<p>देश दर्पण संवाद की यह डेमो रिपोर्ट पाठकों को तेज, साफ और भरोसेमंद जानकारी देने के लिए तैयार की गई है।</p>"
            "<p>समाचार टीम ने स्थानीय संदर्भ, नागरिक सुविधा और जरूरी तथ्यों को सरल भाषा में प्रस्तुत किया है।</p>"
        )
        for index, title in enumerate(headlines):
            article, _ = Article.objects.update_or_create(
                slug=f"home-demo-{index + 1}",
                defaults={
                    "title": title,
                    "short_title": title[:90],
                    "summary": "मुख्य तथ्य, पृष्ठभूमि और जरूरी अपडेट एक ही जगह पढ़ें।",
                    "body": body,
                    "category": categories[index % len(categories)],
                    "state": state,
                    "district": district,
                    "city": city,
                    "author": author,
                    "published_at": timezone.now() - timezone.timedelta(hours=index),
                    "status": Article.Status.PUBLISHED,
                    "featured_image": image_paths[index % len(image_paths)],
                    "is_breaking": index < 4,
                    "is_homepage_hero": index < 3,
                    "is_top_story": index < 6,
                    "is_trending": index in [1, 3, 5, 7, 9],
                    "is_editor_pick": index in [0, 2, 4, 6, 8, 10],
                    "views": 600 - (index * 23),
                },
            )

        gallery, _ = Gallery.objects.update_or_create(
            slug="demo-city-gallery",
            defaults={"title": "शहर की तस्वीरों में आज का दिन", "category": categories[0], "location": city, "cover_image": image_paths[2], "active": True},
        )
        Video.objects.update_or_create(
            slug="demo-evening-bulletin",
            defaults={"title": "शाम की बड़ी खबरें वीडियो बुलेटिन", "youtube_url": "https://www.youtube.com/embed/dQw4w9WgXcQ", "thumbnail": image_paths[1], "category": categories[0], "active": True, "featured": True},
        )

        for index in range(8):
            story, _ = WebStory.objects.update_or_create(
                slug=f"demo-24hr-story-{index + 1}",
                defaults={"title": f"24 घंटे की खास अपडेट {index + 1}", "cover": image_paths[index % len(image_paths)], "category": categories[index % len(categories)], "active": True},
            )
            for slide_index in range(3):
                StorySlide.objects.update_or_create(
                    story=story,
                    order=slide_index,
                    defaults={"heading": f"अपडेट {slide_index + 1}", "text": "यह डेमो वेब स्टोरी स्लाइड है।"},
                )

        self.stdout.write(self.style.SUCCESS("Polished homepage demo data seeded."))
        self.stdout.write(f"Demo editor username: dds_editor | password: {editor_password}")

    def _font(self, size):
        for name in ["arial.ttf", "Nirmala.ttf", "NirmalaB.ttf", "DejaVuSans-Bold.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _make_image(self, path, start, end, label, font_bold, font_small):
        width, height = 1280, 720
        img = Image.new("RGB", (width, height), start)
        draw = ImageDraw.Draw(img)
        for y in range(height):
            ratio = y / height
            color = tuple(
                int(int(start[i:i + 2], 16) * (1 - ratio) + int(end[i:i + 2], 16) * ratio)
                for i in (1, 3, 5)
            )
            draw.line([(0, y), (width, y)], fill=color)
        draw.ellipse((860, -120, 1380, 400), outline=(255, 255, 255), width=3)
        draw.rectangle((72, 468, 640, 590), fill=(227, 30, 40))
        draw.text((96, 488), label, fill="white", font=font_bold)
        draw.text((96, 610), "Desh Darpan Samvad", fill=(235, 240, 249), font=font_small)
        img.save(path, quality=92)
