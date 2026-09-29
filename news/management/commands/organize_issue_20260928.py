from datetime import date

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from galleries.models import Gallery, GalleryImage
from locations.models import City, District, State
from news.models import Article, Category


ISSUE_DATE = date(2026, 9, 28)

# Article IDs are deliberately not used here: titles make this command safe on
# every database, including a restored production backup.
CITY_RULES = {
    "अनंत आनंद से रोशन हुआ इंदौर": ("इंदौर", "इंदौर", "indore"),
    "भोपाल में सीएम का कांग्रेस पर करारा प्रहार": ("भोपाल", "भोपाल", "bhopal"),
    "गुलमर्ग परिसर में": ("भोपाल", "भोपाल", "bhopal"),
    "श्रीअन्न उत्पादन में अग्रणी बना सीधी": ("सीधी", "सीधी", "sidhi"),
    "ग्वालियर में बनेगा टेलीकॉम हब": ("ग्वालियर", "ग्वालियर", "gwalior"),
    "दतिया का सियासी तिलिस्म": ("दतिया", "दतिया", "datia"),
    "भोपाल मास्टर प्लान": ("भोपाल", "भोपाल", "bhopal"),
    "गोविंदपुरा की": ("भोपाल", "भोपाल", "bhopal"),
    "सीधी के नितिन पटेल": ("सीधी", "सीधी", "sidhi"),
    "डीबी मॉल": ("भोपाल", "भोपाल", "bhopal"),
    "‘ब्लड मैन’ निरीक्षक अनुराग झारिया": ("आगर मालवा", "नलखेड़ा", "nalkheda"),
}

# These are Madhya Pradesh stories without one honest, exclusive city. Keeping
# city blank avoids falsely placing a multi-city/state-wide report in one city.
STATE_ONLY_MARKERS = (
    "पर्यावरण और वन्यजीव संरक्षण",
    "इंदौर, भोपाल और ग्वालियर",
    "एमपी में बिप्लब देब",
    "मध्य प्रदेश में दो दिन",
)


class Command(BaseCommand):
    help = "Complete section, location and photo-gallery placement for issue 03."

    def handle(self, *args, **options):
        articles = list(
            Article.objects.filter(published_at__date=ISSUE_DATE).order_by("published_at", "id")
        )
        if len(articles) != 32:
            raise CommandError(f"Expected 32 issue articles, found {len(articles)}")

        mp, _ = State.objects.get_or_create(
            slug="madhya-pradesh", defaults={"name": "मध्य प्रदेश", "active": True}
        )

        city_cache = {}
        for district_name, city_name, city_slug in set(CITY_RULES.values()):
            district_slug = slugify(district_name, allow_unicode=False) or {
                "इंदौर": "indore", "भोपाल": "bhopal", "सीधी": "sidhi",
                "ग्वालियर": "gwalior", "दतिया": "datia", "आगर मालवा": "agar-malwa",
            }[district_name]
            district, _ = District.objects.get_or_create(
                state=mp, slug=district_slug,
                defaults={"name": district_name, "active": True},
            )
            city, _ = City.objects.get_or_create(
                district=district, slug=city_slug,
                defaults={"name": city_name, "active": True},
            )
            city_cache[(district_name, city_name, city_slug)] = city

        for index, article in enumerate(articles):
            article.is_breaking = index < 5
            article.is_homepage_hero = index < 5
            article.is_top_story = index < 8
            article.is_featured = index < 12
            article.is_trending = index < 12
            article.is_editor_pick = index in {12, 13, 14, 15, 16, 17}

            article.state = article.district = article.city = None
            for marker, location in CITY_RULES.items():
                if marker in article.title:
                    city = city_cache[location]
                    article.state = mp
                    article.district = city.district
                    article.city = city
                    break
            else:
                if article.category.slug == "madhya-pradesh" or any(
                    marker in article.title for marker in STATE_ONLY_MARKERS
                ):
                    article.state = mp

            article.save(update_fields=[
                "is_breaking", "is_homepage_hero", "is_top_story", "is_featured",
                "is_trending", "is_editor_pick", "state", "district", "city", "updated_at",
            ])
            Category.objects.filter(pk=article.category_id).update(active=True, show_on_homepage=True)

        gallery, _ = Gallery.objects.update_or_create(
            slug="desh-darpan-issue-03-28-september-2026",
            defaults={
                "title": "देश दर्पण संवाद: 28 सितंबर 2026 की प्रमुख तस्वीरें",
                "description": "अंक 03 की प्रमुख खबरों और घटनाओं की तस्वीरें।",
                "category": articles[0].category,
                "location": articles[0].city,
                "published_at": articles[0].published_at,
                "active": True,
                "seo_title": "28 सितंबर 2026 समाचार फोटो गैलरी",
                "meta_description": "देश दर्पण संवाद अंक 03 की प्रमुख समाचार तस्वीरें।",
            },
        )
        gallery.images.all().delete()
        image_articles = [article for article in articles if article.featured_image]
        for order, article in enumerate(image_articles):
            article.featured_image.open("rb")
            image_data = article.featured_image.read()
            article.featured_image.close()
            item = GalleryImage(
                gallery=gallery, caption=article.title, credit=article.image_credit, order=order
            )
            suffix = article.featured_image.name.rsplit(".", 1)[-1]
            item.image.save(f"issue-03-{order + 1}.{suffix}", ContentFile(image_data), save=True)

        if image_articles:
            image_articles[0].featured_image.open("rb")
            cover_data = image_articles[0].featured_image.read()
            image_articles[0].featured_image.close()
            suffix = image_articles[0].featured_image.name.rsplit(".", 1)[-1]
            gallery.cover_image.save(f"issue-03-cover.{suffix}", ContentFile(cover_data), save=True)

        self.stdout.write(self.style.SUCCESS(
            f"Organized {len(articles)} articles, mapped locations and created {len(image_articles)} gallery images."
        ))
