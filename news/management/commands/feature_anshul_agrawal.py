from django.core.management.base import BaseCommand, CommandError

from news.models import Article


class Command(BaseCommand):
    help = "Feature Anshul Agrawal's AI and digital marketing article on the homepage."

    def handle(self, *args, **options):
        article = Article.objects.filter(title__startswith="AI के दौर में IT और डिजिटल मार्केटिंग").first()
        if article is None:
            raise CommandError("Anshul Agrawal article was not found")
        article.short_title = "अंशुल अग्रवाल का विशेष लेख: AI और डिजिटल मार्केटिंग"
        article.is_top_story = True
        article.is_featured = True
        article.is_editor_pick = True
        article.save(update_fields=["short_title", "is_top_story", "is_featured", "is_editor_pick", "updated_at"])
        self.stdout.write(self.style.SUCCESS(f"Featured article {article.pk}: {article.title}"))
