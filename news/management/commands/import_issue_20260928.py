from datetime import datetime, time, timedelta
from html import escape
from pathlib import Path
import re

import pymupdf
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from news.models import Article, Category


# Coordinates are percentages of the print page, keeping the importer stable
# if this issue is re-exported at a different PDF resolution.
ARTICLES = [
    (1, (12, 11, 98, 42), "अनंत आनंद से रोशन हुआ इंदौर: 103 साल पुरानी परंपरा में उमड़ा लाखों का जनसैलाब", "मध्य प्रदेश", "madhya-pradesh"),
    (1, (13, 41, 65, 83), "भोपाल में सीएम का कांग्रेस पर करारा प्रहार", "राजनीति", "politics"),
    (1, (65, 40, 98, 60), "गुलमर्ग परिसर में ‘गुलमर्ग के राजा’ का भव्य समापन, 21 पौधे लगाकर दिया पर्यावरण संरक्षण का संदेश", "मध्य प्रदेश", "madhya-pradesh"),
    (1, (65, 58, 98, 84), "पर्यावरण और वन्यजीव संरक्षण में सुधार: वन्यजीव प्रेमियों के लिए सुखद खबर", "पर्यावरण", "environment"),
    (1, (3, 87, 98, 99), "भारतीय रेलवे का ‘ग्रीन गियर’: एक बार टैंक फुल, 2200 किमी दौड़ेगी देश की पहली LNG ट्रेन", "देश", "national"),
    (2, (3, 6, 53, 42), "डिजिटल पेमेंट पर ब्रेक: इंदौर, भोपाल और ग्वालियर में दिखा सबसे ज्यादा विरोध, कैश की तरफ लौटे लोग", "व्यापार", "business"),
    (2, (54, 6, 98, 42), "एमपी में बिप्लब देब को मिली भाजपा की कमान: अब बढ़ेगा गणेश सिंह का सियासी कद", "राजनीति", "politics"),
    (2, (3, 40, 53, 55), "श्रीअन्न उत्पादन में अग्रणी बना सीधी जिला, कोदो-कुटकी जैसी मिलेट फसलें हैं संस्कृति की पहचान", "मध्य प्रदेश", "madhya-pradesh"),
    (2, (54, 51, 98, 68), "शिक्षा विभाग की बड़ी पहल: मध्य प्रदेश में दो दिन के भीतर जारी हुए 600 अनुकंपा नियुक्ति आदेश", "शिक्षा", "education"),
    (2, (3, 54, 53, 68), "विकास की दोहरी उड़ान: ग्वालियर में बनेगा टेलीकॉम हब, गडकरी करेंगे ‘सुगम परिवहन सेवा’ का शुभारंभ", "मध्य प्रदेश", "madhya-pradesh"),
    (2, (3, 66, 98, 99), "दतिया का सियासी तिलिस्म: घनश्याम सिंह की विधायकी पर तलवार, क्या फिर होगा उपचुनाव?", "राजनीति", "politics"),
    (3, (3, 5, 76, 35), "चुनाव आयोग में भारी घमासान: मुख्य आयुक्त के फैसलों पर उठे सवाल", "देश", "national"),
    (3, (76, 5, 98, 51), "भारत का बढ़ता रक्षा निर्यात: स्वदेशी हथियारों का बजा डंका", "देश", "national"),
    (3, (3, 34, 76, 72), "मिशन-2027 के लिए भाजपा की नई ब्रिगेड तैयार", "राजनीति", "politics"),
    (3, (3, 71, 76, 99), "भोपाल मास्टर प्लान: ड्राफ्ट प्रकाशन को सुप्रीम कोर्ट की हरी झंडी", "मध्य प्रदेश", "madhya-pradesh"),
    (4, (3, 7, 56, 57), "भारत का युवा और कार्यशील वर्ग—देश के भविष्य की सबसे बड़ी शक्ति", "विचार", "opinion"),
    (4, (56, 7, 98, 32), "सोशल मीडिया—कमाई, कारोबार और ज्ञान का नया केंद्र", "टेक्नोलॉजी", "technology"),
    (4, (56, 31, 98, 58), "GeM के 10 साल—भाग 2: छोटे कारोबारी के लिए रास्ता कितना आसान?", "व्यापार", "business"),
    (4, (3, 57, 98, 99), "नारी शक्ति—परिवार, समाज और राष्ट्र की असली ताकत", "विचार", "opinion"),
    (5, (3, 5, 98, 65), "गोविंदपुरा की ‘रिकॉर्ड ब्रेकर’ जननेता श्रीमती कृष्णा गौर के राजनीतिक सफर और जन्मदिन पर विशेष", "राजनीति", "politics"),
    (5, (3, 69, 98, 99), "किसान के बेटे ने रचा इतिहास, सीधी के नितिन पटेल ने MPPSC असिस्टेंट प्रोफेसर परीक्षा में हासिल की 10वीं रैंक", "शिक्षा", "education"),
    (6, (3, 5, 98, 52), "एशियाई खेल 2026: भारत का समग्र प्रदर्शन", "खेल", "sports"),
    (6, (3, 52, 64, 99), "सात दशकों में पहली बार दिल्ली से बाहर निकले राष्ट्रीय फिल्म पुरस्कार", "मनोरंजन", "entertainment"),
    (6, (64, 52, 98, 99), "द पैराडाइज का बॉक्स ऑफिस पर धमाल: 3 दिन में पार किया 100 करोड़ का आंकड़ा", "मनोरंजन", "entertainment"),
    (7, (3, 5, 53, 53), "रूस का ‘शैडो फ्लीट’—वह प्रतिबंध-भेदी तंत्र जो लगातार बढ़ता जा रहा है", "दुनिया", "world"),
    (7, (53, 5, 98, 53), "दो हजार साल बाद रोशनी में आया प्राचीन रोम का सबसे बड़ा भित्ति-चित्र", "दुनिया", "world"),
    (7, (3, 53, 39, 99), "वैश्विक अर्थव्यवस्था में बड़े उलटफेर की आहट", "व्यापार", "business"),
    (7, (39, 53, 98, 99), "28-30 सितंबर बैंक हड़ताल: जरूरी काम पहले निपटाएं", "व्यापार", "business"),
    (8, (3, 5, 68, 61), "सपनों की कोई उम्र नहीं: मातृत्व से ‘डीबी मॉल’ की ब्रांड प्रतिनिधि बनने तक मधुलिका वाजपेई की उड़ान", "महिला", "women"),
    (8, (68, 5, 98, 61), "रूढ़ियों को तोड़ बॉलीवुड तक उड़ान: 40 लाख दिलों पर राज कर रहीं ‘मधु एसडी किंग’", "मनोरंजन", "entertainment"),
    (8, (3, 61, 47, 99), "विचार: सामाजिक संवेदनाओं और जिम्मेदारी की नई दिशा", "विचार", "opinion"),
    (8, (47, 61, 98, 99), "‘ब्लड मैन’ निरीक्षक अनुराग झारिया का नलखेड़ा में भव्य सम्मान", "मध्य प्रदेश", "madhya-pradesh"),
]


def clean_text(value):
    value = value.replace("\u00ad", "").replace("\u200b", "")
    for mark in "ािीुूृेैोौंः":
        value = value.replace(mark + mark, mark)
    value = re.sub(r"([क-ह])्\1", r"\1", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


class Command(BaseCommand):
    help = "Import the complete 28 September 2026 print issue and its article images."

    def add_arguments(self, parser):
        parser.add_argument("pdf", type=Path)
        parser.add_argument("--refresh-images", action="store_true")

    def handle(self, *args, **options):
        source = options["pdf"].expanduser().resolve()
        if not source.is_file():
            raise CommandError(f"PDF not found: {source}")
        call_command("import_epaper", source, edition_date="2026-09-28", title="देश दर्पण संवाद - अंक 03")
        document = pymupdf.open(source)
        User = get_user_model()
        author = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first() or User.objects.first()
        if author is None:
            raise CommandError("No author account exists")
        base_time = timezone.make_aware(datetime.combine(datetime(2026, 9, 28).date(), time(8, 0)))

        for index, (page_number, pct, title, category_name, category_slug) in enumerate(ARTICLES):
            page = document[page_number - 1]
            x0, y0, x1, y1 = pct
            clip = pymupdf.Rect(page.rect.width*x0/100, page.rect.height*y0/100, page.rect.width*x1/100, page.rect.height*y1/100)
            lines = []
            for block in page.get_text("dict", clip=clip)["blocks"]:
                for line in block.get("lines", []):
                    text = " ".join(span["text"].strip() for span in line["spans"] if span["text"].strip())
                    size = max((span["size"] for span in line["spans"]), default=0)
                    if text and size < 15 and "देश दर्पण" not in text and "सितंबर, 2026" not in text and "MPHIN" not in text and "पंजीयन संख्या" not in text and "प्रकाशक" not in text:
                        lines.append(text)
            plain = clean_text("\n".join(lines))
            paragraphs = [part.strip() for part in re.split(r"\n+", plain) if len(part.strip()) > 20]
            body = "".join(f"<p>{escape(part)}</p>" for part in paragraphs)
            if not body:
                body = f"<p>{escape(title)}</p>"
            summary = " ".join(paragraphs)[:300] if paragraphs else title
            category, _ = Category.objects.get_or_create(slug=category_slug, defaults={"name": category_name, "hindi_name": category_name, "active": True})
            article, _ = Article.objects.update_or_create(title=title, defaults={
                "summary": summary, "body": body, "category": category, "author": author,
                "status": Article.Status.PUBLISHED, "published_at": base_time + timedelta(minutes=index),
                "is_breaking": index < 5, "is_top_story": index < 8,
                "is_featured": index < 12, "is_trending": index < 12,
                "is_editor_pick": index in {15, 16, 17, 18}, "is_homepage_hero": index == 0,
            })
            if index in {8, 9, 30} and article.featured_image:
                article.featured_image.delete(save=True)
            if index not in {8, 9, 30} and (not article.featured_image or options["refresh_images"]):
                candidates = []
                for info in page.get_image_info(xrefs=True):
                    box = pymupdf.Rect(info["bbox"])
                    center = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
                    if info["xref"] and clip.contains(center) and box.width * box.height > 2500 and info["width"] > 250:
                        candidates.append((box.width * box.height, info))
                if candidates:
                    info = max(candidates, key=lambda item: item[0])[1]
                    image_bytes = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(info["bbox"]), alpha=False).tobytes("jpeg", jpg_quality=90)
                    article.featured_image.save(f"issue-2026-09-28-{index+1}.jpg", ContentFile(image_bytes), save=True)
            self.stdout.write(f"Article {index+1}/{len(ARTICLES)}: {article.pk} {article.title}")

        self.stdout.write(self.style.SUCCESS(f"Imported {len(ARTICLES)} articles from issue 03."))
