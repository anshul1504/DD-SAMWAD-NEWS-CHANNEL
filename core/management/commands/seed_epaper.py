from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from locations.models import City

from core.models import EPaperEdition, EPaperPage

EDITION_COUNT = 7  # last 7 days, so the archive strip has real dates to click through


class Command(BaseCommand):
    help = f"Seed {EDITION_COUNT} demo e-paper editions with a real, generated multi-page PDF each."

    def handle(self, *args, **options):
        today = timezone.localdate()
        fonts = {
            "masthead": self._font(52),
            "headline": self._font(40),
            "subhead": self._font(24),
            "body": self._font(20),
            "small": self._font(17),
        }
        created = 0

        for i in range(EDITION_COUNT):
            edition_date = today - timezone.timedelta(days=i)
            created += self._seed_edition(edition_date, None, "मुख्य संस्करण", fonts)

        # One city edition (today only) per real city already in Locations --
        # never a fabricated city list, just whatever cities actually exist.
        for city in City.objects.filter(active=True):
            created += self._seed_edition(today, city, f"{city.name} संस्करण", fonts, city_label=city.name)

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} demo e-paper edition(s)."))

    def _seed_edition(self, edition_date, city, default_title, fonts, city_label=None):
        edition, was_created = EPaperEdition.objects.get_or_create(
            edition_date=edition_date,
            city=city,
            defaults={"title": default_title, "active": True},
        )
        if not was_created and edition.pdf:
            return 0  # don't clobber a real edition an editor already uploaded

        pdf_bytes, page_jpegs = self._make_pdf_and_pages(edition_date, fonts, city_label=city_label)
        slug_bit = city.slug if city else "main"
        edition.pdf.save(f"demo-epaper-{slug_bit}-{edition_date}.pdf", ContentFile(pdf_bytes), save=False)
        edition.cover_image.save(f"demo-epaper-cover-{slug_bit}-{edition_date}.jpg", ContentFile(page_jpegs[0]), save=False)
        edition.page_count = len(page_jpegs)
        edition.title = edition.title or default_title
        edition.active = True
        edition.save()

        edition.pages.all().delete()
        for page_number, jpeg_bytes in enumerate(page_jpegs, start=1):
            page = EPaperPage(edition=edition, page_number=page_number)
            page.image.save(f"demo-epaper-{slug_bit}-{edition_date}-p{page_number}.jpg", ContentFile(jpeg_bytes), save=True)
        return 1

    def _font(self, size):
        # Nirmala first: it has Devanagari glyphs. arial.ttf loads without
        # error but silently renders every Hindi character as a tofu box, so
        # it must never be tried before a font that actually supports Hindi.
        for name in ["Nirmala.ttf", "NirmalaB.ttf", "mangal.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _make_pdf_and_pages(self, edition_date, fonts, city_label=None):
        # A real, valid multi-page PDF -- generated via Pillow (already a
        # project dependency) -- kept only for the download button. The
        # in-site reader instead shows each page as its own JPEG: browser PDF
        # viewers render inconsistently (or not at all) inside an iframe
        # depending on browser/OS/mobile webview, while a plain image never
        # fails to display, and this also matches how real e-paper sites
        # (page-by-page image viewers, not embedded PDFs) actually work.
        width, height = 900, 1272  # roughly A4 aspect, matches the site's 3:4 cover ratio closely enough
        weekday = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"][edition_date.weekday()]
        pages = [self._front_page(width, height, edition_date, weekday, fonts, city_label)]
        for page_num in range(2, 5):
            pages.append(self._inner_page(width, height, page_num, fonts))

        buffer_path = Path(settings.MEDIA_ROOT) / "epaper" / "_tmp_pdf_build.pdf"
        buffer_path.parent.mkdir(parents=True, exist_ok=True)
        pages[0].save(buffer_path, "PDF", save_all=True, append_images=pages[1:])
        pdf_data = buffer_path.read_bytes()
        buffer_path.unlink(missing_ok=True)

        page_jpegs = []
        for page in pages:
            buf = BytesIO()
            page.save(buf, "JPEG", quality=90)
            page_jpegs.append(buf.getvalue())
        return pdf_data, page_jpegs

    def _front_page(self, width, height, edition_date, weekday, fonts, city_label=None):
        navy, red, ink, muted, line = "#0b3474", "#d71920", "#101828", "#667085", "#d0d5dd"
        img = Image.new("RGB", (width, height), "#ffffff")
        draw = ImageDraw.Draw(img)

        # Masthead
        masthead = f"देश दर्पण संवाद - {city_label}" if city_label else "देश दर्पण संवाद"
        draw.text((width / 2, 55), masthead, font=fonts["masthead"], fill=navy, anchor="mm")
        draw.line([40, 100, width - 40, 100], fill=red, width=4)
        draw.text((40, 118), f"{weekday}, {edition_date.strftime('%d %B %Y')}", font=fonts["small"], fill=muted)
        draw.text((width - 40, 118), "डेमो संस्करण · मूल्य ₹0.00", font=fonts["small"], fill=muted, anchor="ra")
        draw.line([40, 150, width - 40, 150], fill=line, width=1)

        # Lead headline block
        draw.text((40, 180), "मुख्य शीर्षक: यहां असली समाचार शीर्षक प्रकाशित होगा", font=fonts["headline"], fill=ink)
        draw.line([40, 240, width - 40, 240], fill=line, width=1)
        self._paragraph(
            draw, (40, 260), width - 80, 3,
            "यह एक डेमो पृष्ठ है। वास्तविक प्रकाशन के लिए एडमिन पैनल से असली PDF अपलोड करें। "
            "जब तक असली संस्करण अपलोड नहीं होता, यह सैंपल पेज केवल ले-आउट दिखाने के लिए है।",
            fonts["subhead"], muted,
        )

        # Three-column body, like a real front page
        col_gap = 30
        col_width = (width - 80 - 2 * col_gap) // 3
        headlines = ["राष्ट्रीय समाचार", "व्यापार और बाजार", "खेल जगत"]
        for i in range(3):
            x = 40 + i * (col_width + col_gap)
            draw.text((x, 400), headlines[i], font=fonts["subhead"], fill=red)
            draw.line([x, 434, x + col_width, 434], fill=line, width=2)
            self._paragraph(
                draw, (x, 450), col_width, 18,
                "डेमो समाचार सामग्री। प्रकाशन हेतु असली लेख इस स्थान पर आएगा। यह केवल स्तंभ की चौड़ाई और पंक्ति दिखाने के लिए भरा गया पाठ है।",
                fonts["body"], ink,
            )
        return img

    def _inner_page(self, width, height, page_num, fonts):
        ink, muted, line = "#101828", "#667085", "#d0d5dd"
        img = Image.new("RGB", (width, height), "#ffffff")
        draw = ImageDraw.Draw(img)
        draw.text((40, 40), "देश दर्पण संवाद", font=fonts["subhead"], fill=ink)
        draw.text((width - 40, 40), f"पेज {page_num}", font=fonts["small"], fill=muted, anchor="ra")
        draw.line([40, 80, width - 40, 80], fill=line, width=2)

        col_gap = 30
        col_width = (width - 80 - col_gap) // 2
        for i in range(2):
            x = 40 + i * (col_width + col_gap)
            draw.text((x, 110), f"अनुभाग {i + 1}", font=fonts["subhead"], fill=ink)
            draw.line([x, 144, x + col_width, 144], fill=line, width=2)
            self._paragraph(
                draw, (x, 160), col_width, 32,
                "डेमो समाचार सामग्री - प्रकाशन हेतु असली फ़ाइल अपलोड करें। यह पाठ केवल ले-आउट दिखाने के लिए है।",
                fonts["body"], muted,
            )
        return img

    def _paragraph(self, draw, position, max_width, max_lines, text, font, fill):
        """Word-wraps `text` to `max_width`, cycling through its words to fill
        exactly `max_lines` -- bounded by line count (not text length), so a
        repeating demo sentence can never overflow its allotted block."""
        words = text.split()
        x0, y = position
        line_height = font.size + 10
        line_words = []
        lines_drawn = 0
        i = 0
        while lines_drawn < max_lines:
            word = words[i % len(words)]
            candidate = " ".join(line_words + [word])
            if draw.textlength(candidate, font=font) > max_width and line_words:
                draw.text((x0, y), " ".join(line_words), font=font, fill=fill)
                y += line_height
                lines_drawn += 1
                line_words = [word]
            else:
                line_words.append(word)
            i += 1
        if line_words and lines_drawn < max_lines:
            draw.text((x0, y), " ".join(line_words), font=font, fill=fill)
