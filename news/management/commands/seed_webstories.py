from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from news.models import Category
from webstories.models import StorySlide, WebStory

STORY_COUNT = 50
SLIDES_PER_STORY = 4

# (category slug, story title, [slide headings])
TOPICS = [
    ("national", "आज की 5 बड़ी राष्ट्रीय खबरें", ["संसद सत्र अपडेट", "नई नीति की घोषणा", "राज्यों से रिपोर्ट", "आर्थिक संकेतक", "आगे क्या"]),
    ("international", "दुनिया भर से आज की सुर्खियां", ["वैश्विक बाजार", "कूटनीतिक बैठक", "जलवायु रिपोर्ट", "अंतरराष्ट्रीय खेल", "विश्लेषण"]),
    ("politics", "राजनीति: आज के बड़े बयान", ["नेताओं के बयान", "चुनावी तैयारी", "गठबंधन की चर्चा", "जनता की प्रतिक्रिया"]),
    ("business", "बाजार अपडेट: शेयर बाजार की चाल", ["सेंसेक्स-निफ्टी", "बड़ी कंपनियां", "क्रिप्टो और सोना", "एक्सपर्ट की राय"]),
    ("sports", "खेल जगत की तस्वीरों में झलक", ["मैच हाइलाइट्स", "खिलाड़ी का प्रदर्शन", "टूर्नामेंट अपडेट", "आगामी मुकाबले"]),
    ("entertainment", "बॉलीवुड और मनोरंजन की खबरें", ["फिल्म रिलीज़", "सेलेब्रिटी अपडेट", "बॉक्स ऑफिस", "OTT हाइलाइट्स"]),
    ("technology", "टेक्नोलॉजी: नए गैजेट्स और अपडेट", ["नया स्मार्टफोन लॉन्च", "AI में नवाचार", "ऐप अपडेट", "टेक टिप्स"]),
    ("lifestyle", "लाइफस्टाइल: सेहत और फैशन टिप्स", ["सुबह की दिनचर्या", "सेहतमंद खानपान", "फैशन ट्रेंड", "घरेलू नुस्खे"]),
    ("education", "शिक्षा जगत के जरूरी अपडेट", ["परीक्षा परिणाम", "प्रवेश प्रक्रिया", "स्कॉलरशिप अपडेट", "करियर गाइड"]),
    ("jobs-career", "आज के नौकरी के बड़े अवसर", ["सरकारी भर्ती", "प्राइवेट सेक्टर", "आवेदन की तारीख", "तैयारी के टिप्स"]),
    ("crime", "अपराध जगत: आज की रिपोर्ट", ["घटना का ब्यौरा", "पुलिस कार्रवाई", "जांच अपडेट", "सुरक्षा सलाह"]),
    ("religion", "धर्म और अध्यात्म: आज के प्रसंग", ["त्योहार की तैयारी", "मंदिर दर्शन", "व्रत-पर्व अपडेट", "आध्यात्मिक विचार"]),
]

PALETTE = [
    ("#0b3474", "#1d4ed8"), ("#7c1d1d", "#e31e28"), ("#0f5132", "#16a34a"),
    ("#4c1d95", "#7c3aed"), ("#7c2d12", "#f59e0b"), ("#155e75", "#0891b2"),
    ("#831843", "#ec4899"), ("#1e293b", "#38bdf8"),
]


class Command(BaseCommand):
    help = f"Seed {STORY_COUNT} sample web stories (with cover + slides) so the homepage's web-story rails have real, recent content to render."

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        image_dir = media_root / "demo-webstories"
        image_dir.mkdir(parents=True, exist_ok=True)

        font_heading = self._font(48)
        categories = {c.slug: c for c in Category.objects.filter(active=True)}

        # A handful of reusable cover images per topic rather than 200 unique
        # renders — the visual variety comes from the palette + title, not from
        # generating a fresh JPEG per slide.
        cover_paths = {}
        for index, (slug, title, _) in enumerate(TOPICS):
            path = image_dir / f"cover-{slug}.jpg"
            start, end = PALETTE[index % len(PALETTE)]
            self._make_image(path, start, end, title, font_heading)
            cover_paths[slug] = f"demo-webstories/{path.name}"

        now = timezone.now()
        created = 0
        for i in range(STORY_COUNT):
            slug_key, base_title, headings = TOPICS[i % len(TOPICS)]
            variant = (i // len(TOPICS)) + 1
            slug = f"demo-webstory-{i + 1}"
            title = base_title if variant == 1 else f"{base_title} (भाग {variant})"
            # Spread across the last ~20 hours so the homepage's "24hr Stories"
            # rail (which filters on published_at) actually has content, not
            # just the general web-stories grid further down the page.
            published_at = now - timezone.timedelta(minutes=i * 24)

            story, was_created = WebStory.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "cover": cover_paths[slug_key],
                    "category": categories.get(slug_key),
                    "published_at": published_at,
                    "active": True,
                },
            )
            created += int(was_created)

            for slide_index in range(SLIDES_PER_STORY):
                heading = headings[slide_index % len(headings)]
                StorySlide.objects.update_or_create(
                    story=story,
                    order=slide_index,
                    defaults={
                        "heading": heading,
                        "text": f"{heading} से जुड़ी संक्षिप्त जानकारी — पूरी खबर के लिए वेबसाइट पर पढ़ें।",
                        "image": cover_paths[slug_key],
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {STORY_COUNT} web stories ({created} new, {STORY_COUNT - created} updated), "
            f"{SLIDES_PER_STORY} slides each."
        ))

    def _font(self, size):
        # Nirmala first: it has Devanagari glyphs. arial.ttf loads without
        # error but silently renders every Hindi character as a tofu box.
        for name in ["Nirmala.ttf", "NirmalaB.ttf", "mangal.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _make_image(self, path, start, end, label, font):
        width, height = 720, 1280
        img = Image.new("RGB", (width, height), start)
        draw = ImageDraw.Draw(img)
        for y in range(height):
            ratio = y / height
            r = int(int(start[1:3], 16) * (1 - ratio) + int(end[1:3], 16) * ratio)
            g = int(int(start[3:5], 16) * (1 - ratio) + int(end[3:5], 16) * ratio)
            b = int(int(start[5:7], 16) * (1 - ratio) + int(end[5:7], 16) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        words = label.split()
        lines, current = [], ""
        for word in words:
            trial = (current + " " + word).strip()
            if draw.textlength(trial, font=font) > width - 80 and current:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)

        total_height = len(lines) * 58
        y = (height - total_height) // 2
        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((width - w) / 2, y), line, font=font, fill="#ffffff")
            y += 58

        img.save(path, "JPEG", quality=82)
