from datetime import datetime, time, timedelta
from pathlib import Path

import pymupdf
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from galleries.models import Gallery, GalleryImage
from locations.models import State
from news.models import Article, Category


ISSUE_DATE = datetime(2026, 10, 19).date()
SOURCE_CREDIT = "देश दर्पण संवाद"
CATEGORIES = {
    "madhya-pradesh": "मध्य प्रदेश", "national": "देश", "politics": "राजनीति",
    "business": "व्यापार", "sports": "खेल", "entertainment": "मनोरंजन",
    "world": "दुनिया", "women": "महिला", "opinion": "विचार", "religion": "धर्म",
}


def story(title, summary, category, page, crop=None):
    return {"title": title, "summary": summary, "category": category, "page": page, "crop": crop}


# Every crop below is a photograph/illustration only.  Newspaper headlines and
# multi-column text are deliberately never used as article images.
STORIES = [
    story("गांधीनगर चुनाव परिणाम: आम आदमी पार्टी का सुपड़ा साफ, कांग्रेस को संजीवनी", "गांधीनगर के चुनाव परिणामों ने स्थानीय राजनीति का समीकरण बदल दिया। आम आदमी पार्टी को झटका लगा, जबकि कांग्रेस के प्रदर्शन और सत्ताधारी दल की स्थिति पर चर्चा तेज है।", "politics", 1, (165, 380, 440, 600)),
    story("रिजर्व बैंक ने बढ़ाया आर्थिक विकास का अनुमान", "वैश्विक व्यापार और टैरिफ से जुड़ी अनिश्चितताओं के बीच भारतीय अर्थव्यवस्था के अनुमान पर रिजर्व बैंक के आकलन ने बाजार और उद्योग जगत का ध्यान खींचा है।", "business", 1),
    story("जनगणना नियमों में बदलाव: निजी कर्मचारी भी करेंगे ड्यूटी", "जनगणना कार्य से जुड़े नियमों में बदलाव के बाद निजी क्षेत्र से सहयोग लेने की व्यवस्था पर चर्चा है। प्रशासनिक तैयारियों और जिम्मेदारियों को लेकर दिशा-निर्देश जारी किए गए हैं।", "national", 1, (485, 800, 625, 970)),
    story("भारत-अमेरिका ट्रेड डील के लीगल ड्राफ्ट पर काम शुरू", "भारत और अमेरिका के बीच पहले चरण की व्यापार वार्ता के बाद कानूनी मसौदे पर काम शुरू होने की खबर है। दोनों देशों के आर्थिक संबंधों को नई दिशा मिलने की उम्मीद जताई जा रही है।", "business", 1),
    story("डिजिटल इंडिया से ग्रामीण अर्थव्यवस्था में 25 प्रतिशत उछाल", "डिजिटल सेवाओं और ऑनलाइन पहुंच के विस्तार से ग्रामीण बाजारों, भुगतान व्यवस्था तथा छोटे कारोबारों में बदलाव को रेखांकित किया गया है।", "business", 1, (650, 1050, 1045, 1230)),
    story("सोयाबीन किसानों के लिए भावांतर भुगतान योजना मंजूर", "कैबिनेट ने सोयाबीन उत्पादकों के लिए भावांतर भुगतान योजना को मंजूरी दी है। योजना का लक्ष्य एमएसपी और बाजार भाव के अंतर से किसानों को राहत देना है।", "madhya-pradesh", 1),
    story("भोपाल के जंबूरी मैदान में गरबे की धूम", "नवरात्रि के उत्सव में भोपाल के जंबूरी मैदान पर गरबा कार्यक्रमों में बड़ी संख्या में लोग शामिल हुए। रंग-बिरंगी पोशाकों और पारंपरिक संगीत ने माहौल को उत्सवमय बनाया।", "religion", 2, (38, 177, 535, 355)),
    story("भोपाल क्रिएटर्स समिट का चौथा संस्करण 24 अक्टूबर को", "मध्य भारत के बड़े क्रिएटर महोत्सव में डिजिटल कंटेंट, नवाचार और युवाओं की भागीदारी पर फोकस रहेगा। कार्यक्रम ताज लेकफ्रंट में आयोजित होना प्रस्तावित है।", "madhya-pradesh", 2, (555, 275, 1030, 385)),
    story("न्यू मार्केट को मिलेगी जाम से मुक्ति, हॉकर्स होंगे शिफ्ट", "भोपाल के न्यू मार्केट में यातायात सुगम करने के लिए हॉकर्स के पुनर्वास और बाजार प्रबंधन की योजना पर प्रशासन काम कर रहा है।", "madhya-pradesh", 2),
    story("मोबाइल से बुक होंगे बस टिकट, एमपी में बसों का अपना डिजिटल प्लेटफॉर्म", "यात्रियों को बस टिकट बुकिंग में सुविधा देने के लिए डिजिटल व्यवस्था तैयार की जा रही है। इससे यात्रा की जानकारी और टिकट उपलब्धता आसानी से मिल सकेगी।", "madhya-pradesh", 2),
    story("कोलकाता के पूजा पंडाल में अव्यवस्था पर सवाल, 17 श्रद्धालुओं की मौत", "कोलकाता के ऐतिहासिक पूजा पंडाल क्षेत्र में अव्यवस्था और हादसे के बाद सुरक्षा प्रबंधों को लेकर गंभीर सवाल उठे हैं। प्रशासनिक जिम्मेदारी और भीड़ प्रबंधन पर चर्चा जारी है।", "national", 3, (35, 236, 278, 372)),
    story("वोट चोरी के मुद्दे पर राहुल गांधी की खुली चुनौती", "वोट चोरी के आरोपों को लेकर राहुल गांधी ने सवाल उठाए और जवाबदेही की मांग की। इस मुद्दे पर राजनीतिक दलों के बीच बयानबाजी तेज हुई है।", "politics", 3, (36, 610, 649, 860)),
    story("निजामपुर उपचुनाव में दिव्या मित्तल उतरीं चुनावी अखाड़े में", "निजामपुर उपचुनाव में उम्मीदवारों की सक्रियता बढ़ गई है। दिव्या मित्तल के मैदान में उतरने से मुकाबले और स्थानीय राजनीतिक समीकरणों पर नजरें टिक गई हैं।", "politics", 3, (675, 578, 1044, 810)),
    story("आशीर्वाद का टीका कार्यक्रम में करोड़ों का घोटाला, जांच की मांग", "कार्यक्रम और टेंडर प्रक्रिया से जुड़े आरोपों को लेकर जांच की मांग उठी है। रिपोर्ट में खर्च, प्रक्रियागत सवालों और जिम्मेदारी तय करने की आवश्यकता का उल्लेख है।", "madhya-pradesh", 3, (38, 1250, 270, 1400)),
    story("सामाजिक संवेदनाओं और जिम्मेदारी की नई दिशा", "संपादकीय में सामाजिक व्यवहार, संवेदनशीलता और नागरिक जिम्मेदारी को मजबूत बनाने की आवश्यकता पर विचार रखा गया है।", "opinion", 4),
    story("लोकतंत्र की चिंता या विपक्ष को राजनीतिक हथियार?", "विचार लेख में लोकतांत्रिक संस्थाओं पर बहस और राजनीतिक विमर्श में उनके इस्तेमाल को लेकर अलग-अलग दृष्टिकोण प्रस्तुत किए गए हैं।", "opinion", 4),
    story("छोटे शहरों को महानगरों जैसे अवसर क्यों नहीं?", "लेख में छोटे शहरों में रोजगार, शिक्षा और तकनीकी सुविधाओं के विस्तार की जरूरत पर जोर दिया गया है।", "opinion", 4),
    story("GeM के 10 साल: युवा भारत के लिए सरकारी कारोबार की 10 सीख", "सरकारी ई-मार्केटप्लेस के दस वर्षों के अनुभवों में पारदर्शी खरीद, गुणवत्ता, नवाचार और युवाओं के लिए नए अवसरों पर विशेष लेख प्रकाशित किया गया है।", "business", 4),
    story("MPPSC की नौकरी छोड़ मार्शल आर्ट्स को बनाया जीवन, विकास शर्मा की कहानी", "विकास शर्मा ने सरकारी नौकरी छोड़कर मार्शल आर्ट्स को अपना करियर बनाया। राष्ट्रीय और अंतरराष्ट्रीय उपलब्धियों के साथ वे युवाओं को खेल और अनुशासन का संदेश दे रहे हैं।", "sports", 5, (35, 365, 330, 870)),
    story("बारिश ने धोई भारत की उम्मीदें, टेस्ट सीरीज 2-2 से बराबर", "बारिश से प्रभावित मुकाबले के बाद टेस्ट श्रृंखला बराबरी पर समाप्त हुई। भारतीय टीम के प्रदर्शन और रिकॉर्ड को लेकर खेल जगत में चर्चा रही।", "sports", 6, (37, 223, 413, 520)),
    story("आईपीएल 2027: दिल्ली कैपिटल्स के नए युग की तैयारी", "आईपीएल 2027 को लेकर दिल्ली कैपिटल्स की रणनीति, संभावित बदलावों और टीम प्रबंधन से जुड़ी खबरों ने क्रिकेट प्रशंसकों का ध्यान खींचा है।", "sports", 6, (425, 218, 770, 470)),
    story("बुमराह की वापसी से न्यूजीलैंड दौरे के लिए भारतीय तेज गेंदबाजी को बल", "न्यूजीलैंड दौरे की तैयारियों के बीच तेज गेंदबाजी आक्रमण को लेकर उम्मीदें बढ़ी हैं। टीम संयोजन और खिलाड़ियों की फिटनेस पर नजर रहेगी।", "sports", 6, (820, 215, 1042, 355)),
    story("बॉक्स ऑफिस पर ‘नय्ये नवेली’ और ‘प्रहार’ का टकराव", "दोनों फिल्मों की रिलीज के साथ बॉक्स ऑफिस पर दिलचस्प मुकाबला देखने को मिल रहा है। दर्शकों की पसंद और शुरुआती कमाई पर नजरें हैं।", "entertainment", 6, (37, 955, 605, 1302)),
    story("ओम: चैप्टर 1 में पहली बार साथ दिखेंगे धनुष और ममूटी", "फिल्म ‘ओम: चैप्टर 1’ में धनुष और ममूटी के साथ आने की चर्चा ने दर्शकों की उत्सुकता बढ़ा दी है।", "entertainment", 6, (620, 990, 1043, 1220)),
    story("फ्रांस में महंगाई और शिक्षा व्यवस्था के विरोध में सड़क पर उतरे लोग", "फ्रांस में महंगाई और शिक्षा से जुड़े मुद्दों पर प्रदर्शन हुए। कई शहरों में विरोध तेज होने से जनजीवन और प्रशासनिक व्यवस्था प्रभावित हुई।", "world", 7, (38, 210, 520, 472)),
    story("रूसी रिफाइनरियों पर हमले जारी, अमेरिका भी खरीदेगा तेल", "ऊर्जा बाजार और रूस-यूक्रेन संघर्ष के बीच रिफाइनरियों पर हमलों तथा तेल आपूर्ति को लेकर अंतरराष्ट्रीय चिंता बनी हुई है।", "world", 7, (548, 322, 783, 562)),
    story("महंगी शिक्षा पर संग्राम: अल्बानिया में छात्रों का प्रदर्शन", "अल्बानिया में शिक्षा की बढ़ती लागत के खिलाफ छात्रों का प्रदर्शन तेज हुआ। विरोध की आंच अन्य देशों तक भी पहुंचने की खबर है।", "world", 7, (807, 210, 1043, 438)),
    story("21 अक्टूबर से खुलेगा देश का सबसे बड़ा जियो आईपीओ", "जियो के प्रस्तावित आईपीओ को लेकर निवेशकों की दिलचस्पी बढ़ी है। बाजार में संभावित आकार और रिकॉर्ड स्तर की चर्चा है।", "business", 7, (38, 1045, 400, 1260)),
    story("भारत में स्टारलिंक पर मंथन: मित्तल और एलन मस्क की बैठक", "सैटेलाइट इंटरनेट और नियामकीय मुद्दों को लेकर भारत में स्टारलिंक की संभावनाओं पर चर्चा तेज है।", "business", 7, (432, 1080, 720, 1240)),
    story("शिक्षा और उद्यम का संगम, लाखों युवाओं का भविष्य संवार रहीं प्राची जैन", "प्राची जैन के काम को शिक्षा, कौशल और युवाओं को रोजगारोन्मुख बनाने की दिशा में प्रेरक पहल के रूप में देखा जा रहा है।", "women", 8, (742, 320, 1043, 702)),
    story("समाज सेवा, गौ-सेवा और महिला सशक्तिकरण की मिसाल: अनुजा प्रशांत पंडित", "अनुजा प्रशांत पंडित के सामाजिक कार्य, महिला सशक्तिकरण और सेवा गतिविधियों को लेकर विशेष रिपोर्ट प्रकाशित की गई है।", "women", 8, (38, 830, 315, 1140)),
    story("गुलमर्ग परिसर में सजा ‘गुलमर्ग की महारानी’ का भव्य दरबार", "आस्था और सनातन संस्कृति से जुड़े आयोजन में श्रद्धालुओं ने सहभागिता की। कार्यक्रम ने सांस्कृतिक एकजुटता का संदेश दिया।", "religion", 8, (38, 1435, 280, 1565)),
]


class Command(BaseCommand):
    help = "Import Desh Darpan Samvad issue 06 (19 October 2026) with clean article images."

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
            self.stdout.write(self.style.SUCCESS(f"Validated issue 06: {len(STORIES)} news articles and 8 e-paper pages."))
            return

        call_command("import_epaper", source, edition_date=ISSUE_DATE.isoformat(), title="देश दर्पण संवाद - अंक 06")
        author = get_user_model().objects.filter(is_superuser=True).first() or get_user_model().objects.filter(is_staff=True).first()
        if author is None:
            raise CommandError("No staff author exists")
        mp, _ = State.objects.get_or_create(slug="madhya-pradesh", defaults={"name": "मध्य प्रदेश", "active": True})
        published_at = timezone.make_aware(datetime.combine(ISSUE_DATE, time(8, 0)))
        imported = []
        for index, entry in enumerate(STORIES):
            category, _ = Category.objects.get_or_create(slug=entry["category"], defaults={"name": CATEGORIES[entry["category"]], "hindi_name": CATEGORIES[entry["category"]], "active": True})
            category.active = category.show_on_homepage = True
            category.save(update_fields=["active", "show_on_homepage"])
            body = (
                f"<p><strong>{entry['summary']}</strong></p>"
                f"<p>{entry['title']} पर देश दर्पण संवाद के 19 अक्टूबर 2026 के मुद्रित अंक में विस्तृत रिपोर्ट प्रकाशित की गई है। उपलब्ध तथ्यों के आधार पर यह विषय पाठकों के लिए महत्वपूर्ण है।</p>"
                f"<h2>मुख्य बिंदु</h2><p>{entry['summary']}</p>"
            )
            article, _ = Article.objects.update_or_create(
                title=entry["title"],
                defaults={
                    "summary": entry["summary"], "body": body, "category": category, "author": author,
                    "status": Article.Status.PUBLISHED, "published_at": published_at + timedelta(minutes=index),
                    "state": mp if entry["category"] == "madhya-pradesh" else None,
                    "image_caption": entry["title"] if entry["crop"] else "", "image_credit": SOURCE_CREDIT if entry["crop"] else "",
                    "seo_title": entry["title"][:180], "meta_description": entry["summary"][:300],
                    "is_breaking": index < 5, "is_homepage_hero": index in {0, 4, 6, 18, 19},
                    "is_top_story": index < 10, "is_featured": index < 18, "is_trending": index < 18,
                    "is_editor_pick": 14 <= index < 20,
                },
            )
            if entry["crop"]:
                pixmap = document[entry["page"] - 1].get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(*entry["crop"]), alpha=False)
                article.featured_image.save(f"issue-2026-10-19-{index + 1:02d}.jpg", ContentFile(pixmap.tobytes("jpeg", jpg_quality=91)), save=True)
            elif article.featured_image:
                article.featured_image.delete(save=False)
                article.featured_image = ""
                article.save(update_fields=["featured_image", "updated_at"])
            imported.append(article)

        gallery, _ = Gallery.objects.update_or_create(
            slug="desh-darpan-issue-06-19-october-2026",
            defaults={"title": "देश दर्पण संवाद: 19 अक्टूबर 2026 की प्रमुख तस्वीरें", "description": "देश दर्पण संवाद अंक 06 की समाचार तस्वीरें।", "category": imported[0].category, "published_at": published_at, "active": True, "seo_title": "19 अक्टूबर 2026 समाचार फोटो गैलरी", "meta_description": "देश दर्पण संवाद अंक 06 की प्रमुख समाचार तस्वीरें।"},
        )
        gallery.images.all().delete()
        with_images = [article for article in imported if article.featured_image]
        for order, article in enumerate(with_images):
            article.featured_image.open("rb")
            image = GalleryImage(gallery=gallery, caption=article.title, credit=SOURCE_CREDIT, order=order)
            image.image.save(f"issue-06-{order + 1:02d}.jpg", ContentFile(article.featured_image.read()), save=True)
            article.featured_image.close()
        if with_images:
            with_images[0].featured_image.open("rb")
            gallery.cover_image.save("issue-06-cover.jpg", ContentFile(with_images[0].featured_image.read()), save=True)
            with_images[0].featured_image.close()
        self.stdout.write(self.style.SUCCESS(f"Imported issue 06: {len(imported)} articles, {len(with_images)} clean article images, 8 e-paper pages."))
