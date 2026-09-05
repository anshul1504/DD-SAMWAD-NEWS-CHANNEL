from django.db import models
from django.utils import timezone


class Advertisement(models.Model):
    class Placement(models.TextChoices):
        HEADER = "header", "Header"
        HOME_TOP = "home_top", "Homepage Top"
        HOME_MIDDLE = "home_middle", "Homepage Middle"
        HOME_BOTTOM = "home_bottom", "Homepage Bottom"
        HOME_VIDEO_BOTTOM = "home_video_bottom", "Homepage Video Bottom"
        SIDEBAR = "sidebar", "Sidebar"
        ARTICLE_TOP = "article_top", "Article Top"
        ARTICLE_MIDDLE = "article_middle", "Article Middle"
        ARTICLE_BOTTOM = "article_bottom", "Article Bottom"
        CATEGORY_PAGE = "category_page", "Category Page"
        MOBILE = "mobile", "Mobile"
        LEADERBOARD = "leaderboard", "Leaderboard"
        BILLBOARD = "billboard", "Billboard"
        RECTANGLE = "rectangle", "Rectangle"
        IN_FEED = "in_feed", "In Feed"
        NATIVE = "native", "Native"
        STICKY_MOBILE = "sticky_mobile", "Sticky Mobile"
        VIDEO = "video", "Video"
        SPONSORED_CONTENT = "sponsored_content", "Sponsored Content"
        POPUP = "popup", "Popup"

    name = models.CharField(max_length=140)
    ad_type = models.CharField(max_length=60, default="image")
    image = models.ImageField(upload_to="ads/", blank=True)
    desktop_image = models.ImageField(upload_to="ads/", blank=True)
    mobile_image = models.ImageField(upload_to="ads/", blank=True)
    target_url = models.URLField(blank=True)
    html_code = models.TextField(blank=True)
    placement = models.CharField(max_length=30, choices=Placement.choices, db_index=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True, db_index=True)
    priority = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-priority", "-id"]

    def __str__(self):
        return self.name

    @property
    def is_live(self):
        now = timezone.now()
        return self.active and (not self.start_date or self.start_date <= now) and (not self.end_date or self.end_date >= now)

# Create your models here.
