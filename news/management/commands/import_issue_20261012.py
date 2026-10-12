from datetime import datetime, time, timedelta
from pathlib import Path

import pymupdf
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from galleries.models import Gallery, GalleryImage
from locations.models import City, District, State
from news.models import Article, Category


ISSUE_DATE = datetime(2026, 10, 12).date()
SOURCE_CREDIT = "देश दर्पण संवाद"
CATEGORY_NAMES = {
    "madhya-pradesh": "मध्य प्रदेश", "national": "देश", "religion": "धर्म",
    "opinion": "विचार", "business": "व्यापार", "sports": "खेल",
    "entertainment": "मनोरंजन", "world": "दुनिया", "women": "महिला",
}


def item(title, summary, category, page, crop=None, city=""):
    return {"title": title, "summary": summary, "category": category, "page": page, "crop": crop, "city": city}


# Crop coordinates are in PDF points and deliberately cover only the photograph printed
# alongside the corresponding report.  Reports without a photograph have crop=None.
ARTICLES = [
    item("सीएम यूथ कॉन्क्लेव में युवाओं के लिए बड़े ऐलान", "5 करोड़ रुपये के आइडिया फंड, निःशुल्क कोचिंग और शोधार्थियों की अनुदान राशि बढ़ाने की घोषणाएं; जुबिन नौटियाल के शो में व्यवस्था बिगड़ने की खबर भी सामने आई।", "madhya-pradesh", 1, (165, 313, 415, 495), "भोपाल"),
    item("नवरात्रि में भक्ति और भव्यता: सजी 2000 से अधिक झांकियां", "शारदीय नवरात्रि के अवसर पर शहरों में देवी प्रतिमाओं और झांकियों के दर्शन के लिए श्रद्धालुओं की भीड़ उमड़ी।", "religion", 1, (420, 225, 570, 385), "भोपाल"),
    item("शारदीय नवरात्रि का शुभारंभ, देशभर में उत्सव का माहौल", "नवरात्रि के पहले दिन मंदिरों में विशेष पूजन हुआ और घरों में घटस्थापना के साथ नौ दिनों के पर्व की शुरुआत हुई।", "religion", 1),
    item("इंदौर में भारत की शानदार जीत, वेस्टइंडीज 14 रन से हारा", "अभिषेक के आक्रामक प्रदर्शन और गेंदबाजों की सधी रणनीति से भारत ने इंदौर में वेस्टइंडीज को 14 रन से हराया।", "sports", 1),
    item("स्वामित्व योजना में लापरवाही पर मुख्य सचिव सख्त", "स्वामित्व योजना की प्रगति की समीक्षा में मुख्य सचिव ने लंबित कामों और रिकॉर्ड अद्यतन में देरी पर अधिकारियों को जवाबदेही तय करने के निर्देश दिए।", "madhya-pradesh", 2, (30, 138, 150, 233), "भोपाल"),
    item("महाकाल के दरबार में दिग्गजों का जमावड़ा", "उज्जैन के महाकाल मंदिर में दर्शन के लिए पहुंचे अतिथियों ने पूजा-अर्चना की और व्यवस्थाओं की सराहना की।", "religion", 2, (278, 535, 389, 672), "उज्जैन"),
    item("सागर के गांव से निकला रोजगार का मॉडल, 20 हजार युवाओं के सारथी बने अभिषेक अथिया", "सागर के ग्रामीण परिवेश से आगे बढ़े अभिषेक अथिया के काम को युवाओं के लिए रोजगार के अवसर तैयार करने वाले मॉडल के रूप में पेश किया गया।", "madhya-pradesh", 2, (428, 194, 680, 330), "भोपाल"),
    item("एमपी ट्रैवल मार्ट में पर्यटन को लगेंगे पंख, 3729 करोड़ के निवेश प्रस्ताव", "मध्य प्रदेश ट्रैवल मार्ट में पर्यटन क्षेत्र के लिए 3729 करोड़ रुपये के निवेश प्रस्तावों और नई संभावनाओं पर चर्चा हुई।", "madhya-pradesh", 2, (30, 805, 310, 928), "भोपाल"),
    item("भोपाल में निकला वुमन्स सॉलिडेरिटी मार्च", "महिलाओं ने समान अवसर, सुरक्षा और स्वतंत्र आवाजाही की मांगों के साथ भोपाल में वुमन्स सॉलिडेरिटी मार्च निकाला।", "women", 2, (500, 950, 680, 1085), "भोपाल"),
    item("पीएम मोदी के 25 साल: नया मंत्र ‘वी विल डू इट’", "प्रधानमंत्री नरेंद्र मोदी के सार्वजनिक जीवन के 25 वर्ष पूरे होने के संदर्भ में विकास, संकल्प और आगे की कार्ययोजना पर संदेश दिया गया।", "national", 3, (35, 140, 350, 372), "नई दिल्ली"),
    item("कंटेंट क्रिएटर्स और Gen-Z से नितिन नवीन का संवाद", "कंटेंट क्रिएटर्स और युवा पीढ़ी के साथ संवाद में डिजिटल भागीदारी, रचनात्मकता और जिम्मेदार संवाद पर जोर दिया गया।", "national", 3, (35, 600, 355, 800), "नई दिल्ली"),
    item("दिल्ली पुलिस के चक्रव्यूह में फंसा प्रदर्शन", "अंतर-मंतर कूच को रोकने के लिए दिल्ली में व्यापक सुरक्षा व्यवस्था की गई; कई नेताओं को हिरासत में लिए जाने की खबर है।", "national", 3, (370, 595, 680, 680), "नई दिल्ली"),
    item("AI के दौर में IT और डिजिटल मार्केटिंग का बदलता स्वरूप", "कृत्रिम बुद्धिमत्ता के बढ़ते उपयोग ने आईटी और डिजिटल मार्केटिंग में कौशल, कार्यप्रणाली और रोजगार की जरूरतों को तेजी से बदला है।", "opinion", 4),
    item("11 अक्टूबर से शारदीय नवरात्र प्रारंभ, 20 अक्टूबर को होगा विसर्जन", "पंचांग के अनुसार शारदीय नवरात्रि और विजयादशमी से जुड़े प्रमुख पर्वों की तिथियां प्रकाशित की गई हैं।", "religion", 4),
    item("GeM के 10 साल: युवा भारत के लिए सरकारी कारोबार की 10 सीख", "सरकारी ई-मार्केटप्लेस के दस वर्ष पूरे होने के अवसर पर पारदर्शी खरीद, नवाचार और युवाओं के लिए अवसरों पर विशेष लेख।", "business", 4),
    item("जमीन से जुड़ी रियासत, विकास की राह पर धौहनी", "गांव की पगडंडियों से विधानसभा तक पहुंचे कुंवर सिंह टेकाम के जनसंपर्क, क्षेत्रीय विकास और धौहनी की प्राथमिकताओं पर विशेष रिपोर्ट।", "madhya-pradesh", 5, (35, 180, 405, 350), "धौहनी"),
    item("249 रन भी पड़े कम: रांची में भारतीय गेंदबाजों की पिटाई", "रांची मुकाबले में 249 रन का स्कोर भी भारत के लिए पर्याप्त नहीं रहा; गेंदबाजी की चूक ने मैच का रुख बदल दिया।", "sports", 6, (35, 165, 150, 300), "रांची"),
    item("अरुण जेटली स्टेडियम में मरम्मत, भारत-श्रीलंका वनडे दिल्ली से बाहर", "अरुण जेटली स्टेडियम में चल रहे मरम्मत कार्य के कारण 13 दिसंबर का भारत-श्रीलंका वनडे दिल्ली में नहीं खेला जाएगा।", "sports", 6, (425, 180, 680, 315), "नई दिल्ली"),
    item("‘दृश्यम 3: द कन्क्लूजन’ ने तोड़े अजय देवगन के रिकॉर्ड", "अजय देवगन की ‘दृश्यम 3: द कन्क्लूजन’ को लेकर दर्शकों की उत्सुकता बढ़ी है और फिल्म से जुड़े नए रिकॉर्ड की चर्चा है।", "entertainment", 6, (33, 650, 415, 880)),
    item("कमल हासन के बयान पर कंगना का तंज, एलन मस्क को भी जवाब", "कमल हासन के ‘भारत किसी का गुलाम नहीं’ वाले बयान पर कंगना रनौत की प्रतिक्रिया और एलन मस्क को लेकर टिप्पणी चर्चा में रही।", "entertainment", 6, (425, 665, 680, 870)),
    item("नेतन्याहू के खिलाफ अरेस्ट वारंट से भड़का अमेरिका", "नेतन्याहू के खिलाफ अरेस्ट वारंट को लेकर अंतरराष्ट्रीय राजनीति में प्रतिक्रिया तेज हुई और अमेरिका की आपत्ति सामने आई।", "world", 7, (35, 170, 150, 300)),
    item("फ्लोरिडा में ‘इसायस’ तूफान का कहर, 9 लाख घरों की बिजली गुल", "फ्लोरिडा में तेज हवाओं वाले तूफान ‘इसायस’ से बड़े पैमाने पर बिजली आपूर्ति बाधित हुई और राहत कार्य शुरू किए गए।", "world", 7, (425, 250, 680, 430)),
    item("5 करोड़ से कम की GST गड़बड़ी पर अब नहीं होगी गिरफ्तारी", "छोटे कारोबारियों को राहत देने वाली जीएसटी व्यवस्था में 5 करोड़ रुपये से कम की गड़बड़ी के मामलों पर गिरफ्तारी नहीं होने का प्रावधान चर्चा में है।", "business", 7, (35, 655, 280, 800)),
    item("इंडिया मोबाइल कांग्रेस 2026: ‘सर्विस नेशन’ से ‘प्रोडक्ट नेशन’ बनने का भारत का दावा", "इंडिया मोबाइल कांग्रेस 2026 में भारत ने नवाचार, तकनीक और उत्पाद निर्माण के क्षेत्र में आगे बढ़ने की दिशा प्रस्तुत की।", "business", 7, (290, 665, 680, 790)),
    item("वकालत से ‘मिसेज सेंट्रल इंडिया’ तक: डॉ. आयुषी की प्रेरक दास्तान", "डॉ. आयुषी ने वकालत, उद्यमिता और ‘मिसेज सेंट्रल इंडिया’ के मंच तक के अपने सफर से महिलाओं के लिए प्रेरक उदाहरण पेश किया।", "women", 8, (32, 158, 240, 328), "भोपाल"),
    item("70 की उम्र में भी फिटनेस का जुनून: पूर्व नौसेना अधिकारी महेंद्र सिंह की कहानी", "पूर्व नौसेना अधिकारी महेंद्र सिंह ने 70 वर्ष की आयु में भी नियमित फिटनेस और अनुशासन से सक्रिय जीवन का संदेश दिया।", "women", 8, (32, 800, 245, 1010), "भोपाल"),
]


class Command(BaseCommand):
    help = "Import the complete 12 October 2026 print issue with clean articles and source photographs."

    def add_arguments(self, parser):
        parser.add_argument("pdf", type=Path)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        source = options["pdf"].expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".pdf":
            raise CommandError(f"PDF not found: {source}")
        document = pymupdf.open(source)
        if document.page_count != 8:
            raise CommandError(f"Expected 8 pages, found {document.page_count}")
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Validated issue 05: {len(ARTICLES)} articles, 8 e-paper pages."))
            return

        call_command("import_epaper", source, edition_date=ISSUE_DATE.isoformat(), title="देश दर्पण संवाद - अंक 05")
        User = get_user_model()
        author = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
        if author is None:
            raise CommandError("No staff author exists")
        desk_user, _ = User.objects.get_or_create(username="ddsamvad-desk", defaults={"is_active": True})
        desk_user.set_unusable_password()
        desk_user.save(update_fields=["password"])

        mp, _ = State.objects.get_or_create(slug="madhya-pradesh", defaults={"name": "मध्य प्रदेश", "active": True})
        cities = {}
        for city_name in sorted({entry["city"] for entry in ARTICLES if entry["city"]}):
            safe_slug = city_name.encode("ascii", "ignore").decode().lower().replace(" ", "-") or f"city-{len(cities) + 1}"
            district, _ = District.objects.get_or_create(state=mp, slug=safe_slug, defaults={"name": city_name, "active": True})
            cities[city_name], _ = City.objects.get_or_create(district=district, slug=safe_slug, defaults={"name": city_name, "active": True})

        Article.objects.filter(status=Article.Status.PUBLISHED).update(is_breaking=False, is_homepage_hero=False, is_top_story=False, is_featured=False, is_trending=False, is_editor_pick=False)
        published_at = timezone.make_aware(datetime.combine(ISSUE_DATE, time(8, 0)))
        imported = []
        for index, entry in enumerate(ARTICLES):
            category, _ = Category.objects.get_or_create(slug=entry["category"], defaults={"name": CATEGORY_NAMES[entry["category"]], "hindi_name": CATEGORY_NAMES[entry["category"]], "active": True})
            category.active = category.show_on_homepage = True
            category.save(update_fields=["active", "show_on_homepage"])
            city = cities.get(entry["city"])
            body = "".join((f"<p><strong>{entry['summary']}</strong></p>", f"<p>{entry['title']} पर देश दर्पण संवाद के मुद्रित अंक में विस्तार से रिपोर्ट प्रकाशित की गई है। उपलब्ध जानकारी के आधार पर यह विषय पाठकों के लिए महत्वपूर्ण है।</p>", "<h2>मुख्य बिंदु</h2>", f"<p>{entry['summary']}</p>"))
            article, _ = Article.objects.update_or_create(
                title=entry["title"],
                defaults={"summary": entry["summary"], "body": body, "category": category, "author": author, "status": Article.Status.PUBLISHED, "published_at": published_at + timedelta(minutes=index), "state": mp if city or entry["category"] == "madhya-pradesh" else None, "district": city.district if city else None, "city": city, "image_caption": entry["title"] if entry["crop"] else "", "image_credit": SOURCE_CREDIT if entry["crop"] else "", "seo_title": entry["title"][:180], "meta_description": entry["summary"][:300], "is_breaking": index < 5, "is_homepage_hero": index < 4, "is_top_story": index < 9, "is_featured": index < 15, "is_trending": index < 15, "is_editor_pick": 15 <= index < 20},
            )
            if entry["crop"]:
                pixmap = document[entry["page"] - 1].get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(*entry["crop"]), alpha=False)
                article.featured_image.save(f"issue-2026-10-12-{index + 1:02d}.jpg", ContentFile(pixmap.tobytes("jpeg", jpg_quality=91)), save=True)
            elif article.featured_image:
                article.featured_image.delete(save=False)
                article.featured_image = ""
                article.save(update_fields=["featured_image", "updated_at"])
            imported.append(article)

        gallery, _ = Gallery.objects.update_or_create(slug="desh-darpan-issue-05-12-october-2026", defaults={"title": "देश दर्पण संवाद: 12 अक्टूबर 2026 की प्रमुख तस्वीरें", "description": "देश दर्पण संवाद अंक 05 की प्रमुख समाचार तस्वीरें।", "category": imported[0].category, "location": imported[0].city, "published_at": published_at, "active": True, "seo_title": "12 अक्टूबर 2026 समाचार फोटो गैलरी", "meta_description": "देश दर्पण संवाद अंक 05 की प्रमुख समाचार तस्वीरें।"})
        gallery.images.all().delete()
        with_images = [article for article in imported if article.featured_image]
        for order, article in enumerate(with_images):
            article.featured_image.open("rb")
            image = GalleryImage(gallery=gallery, caption=article.title, credit=SOURCE_CREDIT, order=order)
            image.image.save(f"issue-05-{order + 1:02d}.jpg", ContentFile(article.featured_image.read()), save=True)
            article.featured_image.close()
        if with_images:
            with_images[0].featured_image.open("rb")
            gallery.cover_image.save("issue-05-cover.jpg", ContentFile(with_images[0].featured_image.read()), save=True)
            with_images[0].featured_image.close()
        self.stdout.write(self.style.SUCCESS(f"Imported issue 05: {len(imported)} articles, {len(with_images)} source images, 8 e-paper pages."))
