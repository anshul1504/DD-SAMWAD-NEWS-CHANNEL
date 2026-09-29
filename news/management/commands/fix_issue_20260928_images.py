from datetime import date
from pathlib import Path

import pymupdf
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from news.models import Article


ISSUE_DATE = date(2026, 9, 28)

# Hand-checked against the print layout. Values are page number and percentage
# coordinates around the actual visual, not the whole article column.
CORRECT_CROPS = {
    4: (1, (61, 92, 78.5, 98.5)),   # LNG locomotive only; exclude text and circular inset
    12: (3, (77, 11, 98, 26)),      # defence export / BrahMos visual
    17: (4, (55, 40, 98, 47)),      # GeM explainer graphic
    18: (4, (3, 78, 14, 85)),       # Nari Shakti author portrait
    21: (6, (3, 12, 41, 29)),       # Asian Games lead team photograph
    22: (6, (3, 66, 31, 77)),       # National Film Awards presentation
}

# The paper has no clean, story-specific photograph for these pieces. Showing
# no image is more accurate than reusing a neighbouring portrait or event shot.
NO_IMAGE = {7, 8, 9, 13, 15, 26, 29, 30}


class Command(BaseCommand):
    help = "Replace wrong automatic crops in the 28 September issue with hand-verified images."

    def add_arguments(self, parser):
        parser.add_argument("pdf", type=Path)

    def handle(self, *args, **options):
        source = options["pdf"].expanduser().resolve()
        if not source.is_file():
            raise CommandError(f"PDF not found: {source}")
        articles = list(Article.objects.filter(published_at__date=ISSUE_DATE).order_by("published_at", "id"))
        if len(articles) != 32:
            raise CommandError(f"Expected 32 issue articles, found {len(articles)}")

        document = pymupdf.open(source)
        for index in NO_IMAGE:
            article = articles[index]
            if article.featured_image:
                article.featured_image.delete(save=True)
            self.stdout.write(f"No image: article {index + 1}")

        for index, (page_number, pct) in CORRECT_CROPS.items():
            page = document[page_number - 1]
            x0, y0, x1, y1 = pct
            clip = pymupdf.Rect(
                page.rect.width * x0 / 100, page.rect.height * y0 / 100,
                page.rect.width * x1 / 100, page.rect.height * y1 / 100,
            )
            data = page.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), clip=clip, alpha=False).tobytes(
                "jpeg", jpg_quality=92
            )
            article = articles[index]
            if article.featured_image:
                article.featured_image.delete(save=False)
            article.featured_image.save(
                f"issue-2026-09-28-{index + 1}-verified-v2.jpg", ContentFile(data), save=True
            )
            self.stdout.write(f"Corrected: article {index + 1}")

        self.stdout.write(self.style.SUCCESS(
            f"Verified {len(CORRECT_CROPS)} crops and removed {len(NO_IMAGE)} incorrect/unsupported images."
        ))
