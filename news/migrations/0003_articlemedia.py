import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("news", "0002_alter_article_youtube_url")]

    operations = [
        migrations.CreateModel(
            name="ArticleMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(blank=True, upload_to="articles/gallery/%Y/%m/")),
                ("video", models.FileField(blank=True, upload_to="articles/videos/%Y/%m/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["mp4", "webm", "ogg", "mov", "m4v"])])),
                ("caption", models.CharField(blank=True, max_length=220)),
                ("credit", models.CharField(blank=True, max_length=120)),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("article", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="media_items", to="news.article")),
            ],
            options={"ordering": ["display_order", "pk"]},
        ),
    ]
