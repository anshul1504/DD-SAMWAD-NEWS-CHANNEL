from pathlib import Path

import pymupdf
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from core.models import EPaperEdition, EPaperPage


class Command(BaseCommand):
    help = "Import a real PDF edition and render every page for the web reader."

    def add_arguments(self, parser):
        parser.add_argument("pdf", type=Path)
        parser.add_argument("--date", required=True, dest="edition_date")
        parser.add_argument("--title", default="मुख्य संस्करण")

    def handle(self, *args, **options):
        source = options["pdf"].expanduser().resolve()
        edition_date = parse_date(options["edition_date"])
        if not source.is_file() or source.suffix.lower() != ".pdf":
            raise CommandError(f"PDF not found: {source}")
        if edition_date is None:
            raise CommandError("--date must be YYYY-MM-DD")

        document = pymupdf.open(source)
        if document.page_count < 1:
            raise CommandError("The PDF has no pages")

        edition, _ = EPaperEdition.objects.get_or_create(
            edition_date=edition_date,
            city=None,
            defaults={"title": options["title"]},
        )
        edition.title = options["title"]
        edition.active = True
        edition.page_count = document.page_count
        edition.pdf.save(source.name, ContentFile(source.read_bytes()), save=False)

        rendered_pages = []
        for number, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
            rendered_pages.append((number, pixmap.tobytes("jpeg", jpg_quality=88)))

        edition.cover_image.save(
            f"desh-darpan-{edition_date}-cover.jpg",
            ContentFile(rendered_pages[0][1]),
            save=False,
        )
        edition.save()

        edition.pages.all().delete()
        for number, image_bytes in rendered_pages:
            page = EPaperPage(edition=edition, page_number=number)
            page.image.save(
                f"desh-darpan-{edition_date}-page-{number}.jpg",
                ContentFile(image_bytes),
                save=True,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported edition {edition.pk} ({edition_date}) with {document.page_count} pages."
            )
        )
