from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from news.models import Article
from webstories.models import StorySlide, WebStory

STORIES = [
    ("फरार CSP नेहा पच्चीसिया", "csp-neha-pachisia-high-court-decision", [("हाईकोर्ट में फैसला सुरक्षित", "निलंबित CSP नेहा पच्चीसिया की याचिका पर दोनों पक्षों की दलीलें पूरी हुईं।"), ("अभियोजन के बड़े दावे", "सरकारी पक्ष ने सह-आरोपी से संबंध और पद के कथित दुरुपयोग से जुड़े बयान रखे।"), ("1.07 करोड़ की जमीन का मामला", "आरोप है कि जमीन दबाव बनाकर 18.20 लाख रुपये में एजेंट के नाम लिखवाई गई।"), ("लुकआउट सर्कुलर जारी", "विदेश जाने की आशंका के बीच एसआईटी और साइबर टीम तलाश कर रही है।")]),
    ("साइबर ठगी से सावधान", "whatsapp-bank-fraud-safety-alert", [("WhatsApp बैंक अलर्ट से सावधान", "डराने वाले debit संदेश पर तुरंत जवाब देने या लिंक खोलने से बचें।"), ("वायरल ‘NO’ दावे की पुष्टि नहीं", "सिर्फ जवाब देने से फोन का नियंत्रण मिलने वाले दावे की आधिकारिक पुष्टि उपलब्ध नहीं है।"), ("खाता केवल official app में जांचें", "OTP, UPI PIN, ATM PIN, कार्ड विवरण या बैंकिंग पासवर्ड कभी साझा न करें।"), ("ठगी हो तो तुरंत 1930", "बैंक को सूचना दें और National Cyber Crime Reporting Portal पर शिकायत दर्ज करें।")]),
    ("280 करोड़ की बंपर कमाई", "hanuman-ansh-satvik-sharma-bhopal", [("‘हनुमान अंश’ में भोपाल का डंका", "फिल्म की सफलता के बीच आठ वर्षीय सात्विक शर्मा ने दर्शकों का दिल जीता।"), ("‘शुभंकर’ का अहम किरदार", "कठिन और संस्कृतनिष्ठ संवादों को सात्विक ने आत्मविश्वास के साथ निभाया।"), ("चार साल की उम्र से अभिनय", "वेब सीरीज और विज्ञापनों के बाद यह फिल्म उनके करियर का बड़ा पड़ाव बनी।"), ("राजधानी के लिए गौरव", "नन्हा कलाकार भोपाल की नई पहचान बना।")]),
]

class Command(BaseCommand):
    help = "Publish web-story versions of the three verified newsroom articles."
    def handle(self, *args, **options):
        for position, (start, slug, slides) in enumerate(STORIES):
            article = Article.objects.filter(title__startswith=start, status=Article.Status.PUBLISHED).first()
            if article is None:
                raise CommandError(f"Published article not found: {start}")
            story, _ = WebStory.objects.update_or_create(slug=slug, defaults={"title": article.title, "cover": article.featured_image.name if article.featured_image else "", "category": article.category, "published_at": timezone.now() - timezone.timedelta(minutes=position), "active": True, "seo_title": (article.seo_title or article.title)[:180], "meta_description": article.summary[:300]})
            story.slides.all().delete()
            article_url = f"{settings.SITE_URL.rstrip('/')}{article.get_absolute_url()}"
            for order, (heading, text) in enumerate(slides):
                StorySlide.objects.create(story=story, image=article.featured_image.name if article.featured_image else "", heading=heading, text=text, cta_label="पूरी खबर पढ़ें" if order == len(slides) - 1 else "", cta_url=article_url if order == len(slides) - 1 else "", order=order)
            self.stdout.write(f"Published web story {story.pk}: {story.slug}")
