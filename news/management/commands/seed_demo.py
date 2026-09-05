import os

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import ReporterProfile
from advertisements.models import Advertisement
from core.models import SiteSettings
from galleries.models import Gallery, GalleryImage
from liveblog.models import LiveBlog, LiveUpdate
from locations.models import City, District, State
from news.models import Article, Category, Tag
from videos.models import Video
from webstories.models import StorySlide, WebStory


class Command(BaseCommand):
    help = "Seed fictional demo content for Desh Darpan Samvad."

    def handle(self, *args, **options):
        SiteSettings.load()
        groups = {name: Group.objects.get_or_create(name=name)[0] for name in ["Admin", "Editor", "Reporter", "SEO Manager"]}
        for codename in ["add_article", "change_article", "view_article"]:
            perm = Permission.objects.get(codename=codename)
            groups["Reporter"].permissions.add(perm)
        for codename in ["change_article", "view_article"]:
            groups["Editor"].permissions.add(Permission.objects.get(codename=codename))

        admin_password = os.getenv("DEMO_ADMIN_PASSWORD") or get_random_string(14)
        reporter_password = os.getenv("DEMO_REPORTER_PASSWORD") or get_random_string(14)
        admin, _ = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True, "email": "admin@example.com"})
        admin.set_password(admin_password)
        admin.save()
        reporter, _ = User.objects.get_or_create(username="reporter", defaults={"is_staff": True, "email": "reporter@example.com", "first_name": "रिपोर्टर"})
        reporter.set_password(reporter_password)
        reporter.groups.add(groups["Reporter"])
        reporter.save()

        state, _ = State.objects.get_or_create(name="मध्य प्रदेश", slug="madhya-pradesh")
        district_names = ["इंदौर", "भोपाल", "उज्जैन", "जबलपुर", "ग्वालियर"]
        cities = []
        for name in district_names:
            district, _ = District.objects.get_or_create(state=state, name=name, slug=slugify(name, allow_unicode=True))
            city, _ = City.objects.get_or_create(district=district, name=f"{name} सिटी", slug=f"{slugify(name, allow_unicode=True)}-city")
            cities.append(city)

        profile, _ = ReporterProfile.objects.get_or_create(user=reporter, defaults={"display_name": "अनिल वर्मा", "slug": "anil-verma", "designation": "स्टाफ रिपोर्टर", "city": cities[0]})
        category_data = [
            ("Home", "होम"), ("Madhya Pradesh", "मध्य प्रदेश"), ("National", "देश"), ("World", "विदेश"),
            ("Politics", "राजनीति"), ("Business", "बिजनेस"), ("Sports", "खेल"), ("Entertainment", "मनोरंजन"),
            ("Education", "शिक्षा"), ("Technology", "टेक्नोलॉजी"), ("Lifestyle", "लाइफस्टाइल"), ("Religion", "धर्म"),
            ("Crime", "अपराध"), ("Agriculture", "कृषि"), ("Jobs", "नौकरी"), ("Government Schemes", "सरकारी योजना"), ("Viral", "वायरल"),
        ]
        categories = []
        for order, (name, hindi) in enumerate(category_data):
            cat, _ = Category.objects.get_or_create(slug=slugify(name), defaults={"name": name, "hindi_name": hindi, "display_order": order})
            categories.append(cat)
        tags = [Tag.objects.get_or_create(name=name, slug=slugify(name, allow_unicode=True))[0] for name in ["विकास", "मौसम", "चुनाव", "युवा", "बाजार"]]

        headlines = [
            "इंदौर में तेज बारिश के बाद कई इलाकों में जलभराव, नगर निगम ने कंट्रोल रूम सक्रिय किया",
            "मध्य प्रदेश सरकार ने नई जनकल्याण योजना की घोषणा की, ग्रामीण परिवारों को मिलेगा लाभ",
            "भारतीय टीम ने रोमांचक मुकाबले में शानदार जीत दर्ज की",
            "स्कूलों में डिजिटल क्लासरूम अभियान का नया चरण शुरू",
            "स्थानीय बाजार में त्योहारी खरीदारी से कारोबारियों में उत्साह",
            "युवाओं के लिए रोजगार मेले में हजारों पदों पर आवेदन शुरू",
            "कृषि मंडी में सोयाबीन की आवक बढ़ी, किसानों को बेहतर दाम की उम्मीद",
            "शहर की प्रमुख सड़क पर यातायात व्यवस्था में बदलाव लागू",
        ]
        body = "<p>यह डेमो समाचार सामग्री है। इसमें स्थानीय संदर्भ, नागरिक सरोकार और प्रशासनिक अपडेट को सरल भाषा में प्रस्तुत किया गया है।</p><p>समाचार टीम ने बताया कि व्यवस्था को बेहतर बनाने के लिए संबंधित विभाग लगातार निगरानी कर रहे हैं।</p>"
        for i in range(48):
            title = headlines[i % len(headlines)]
            article, created = Article.objects.get_or_create(
                slug=f"demo-news-{i + 1}",
                defaults={
                    "title": f"{title} - {i + 1}",
                    "summary": "पाठकों के लिए जरूरी अपडेट और पृष्ठभूमि एक ही जगह।",
                    "body": body,
                    "category": categories[(i % (len(categories) - 1)) + 1],
                    "state": state,
                    "district": cities[i % len(cities)].district,
                    "city": cities[i % len(cities)],
                    "author": reporter,
                    "reporter": profile,
                    "published_at": timezone.now() - timezone.timedelta(hours=i),
                    "status": Article.Status.PUBLISHED,
                    "is_breaking": i < 5,
                    "is_homepage_hero": i < 5,
                    "is_top_story": i % 7 == 0,
                    "is_trending": i % 5 == 0,
                    "is_editor_pick": i % 6 == 0,
                    "views": 100 + i * 17,
                },
            )
            article.tags.set(tags[: (i % len(tags)) + 1])

        gallery, _ = Gallery.objects.get_or_create(title="मध्य प्रदेश की तस्वीरें", slug="madhya-pradesh-photos", defaults={"category": categories[1], "location": cities[0], "description": "डेमो फोटो गैलरी"})
        GalleryImage.objects.get_or_create(gallery=gallery, order=1, defaults={"caption": "शहर का दृश्य"})
        Video.objects.get_or_create(title="आज की बड़ी खबरें", slug="today-top-video", defaults={"youtube_url": "https://www.youtube.com/embed/dQw4w9WgXcQ", "category": categories[2], "description": "डेमो वीडियो समाचार", "featured": True})
        story, _ = WebStory.objects.get_or_create(title="सुबह की पांच जरूरी खबरें", slug="morning-five-news", defaults={"category": categories[2]})
        for i in range(5):
            StorySlide.objects.get_or_create(story=story, order=i, defaults={"heading": f"अपडेट {i + 1}", "text": "संक्षिप्त डेमो वेब स्टोरी स्लाइड।"})
        live, _ = LiveBlog.objects.get_or_create(title="विधानसभा अपडेट लाइव", slug="vidhansabha-live", defaults={"status": LiveBlog.Status.LIVE, "category": categories[4], "location": cities[1]})
        LiveUpdate.objects.get_or_create(live_blog=live, heading="पहला अपडेट", defaults={"body": "लाइव ब्लॉग में ताजा अपडेट जोड़ा गया।", "is_breaking": True})
        Advertisement.objects.get_or_create(name="Demo Header Ad", placement=Advertisement.Placement.HOME_TOP, defaults={"active": True, "priority": 10})
        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
        self.stdout.write(f"Admin username: admin | password: {admin_password}")
        self.stdout.write(f"Reporter username: reporter | password: {reporter_password}")
