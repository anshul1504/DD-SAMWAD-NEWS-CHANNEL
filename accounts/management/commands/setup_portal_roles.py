from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand


ROLE_PERMISSIONS = {
    "Guest": [],
    "Admin": [
        "view_user", "add_user", "change_user",
        "view_article", "add_article", "change_article", "delete_article",
        "view_category", "add_category", "change_category", "delete_category",
        "view_tag", "add_tag", "change_tag", "delete_tag",
        "view_advertisement", "add_advertisement", "change_advertisement", "delete_advertisement",
        "view_gallery", "add_gallery", "change_gallery", "delete_gallery",
        "view_galleryimage", "add_galleryimage", "change_galleryimage", "delete_galleryimage",
        "view_video", "add_video", "change_video", "delete_video",
        "view_webstory", "add_webstory", "change_webstory", "delete_webstory",
        "view_storyslide", "add_storyslide", "change_storyslide", "delete_storyslide",
        "view_liveblog", "add_liveblog", "change_liveblog", "delete_liveblog",
        "view_liveupdate", "add_liveupdate", "change_liveupdate", "delete_liveupdate",
    ],
    "Editor": [
        "view_article", "add_article", "change_article",
        "view_category", "change_category",
        "view_tag", "add_tag", "change_tag",
        "view_gallery", "change_gallery",
        "view_video", "change_video",
        "view_webstory", "change_webstory",
        "view_liveblog", "change_liveblog",
    ],
    "Reporter": [
        "view_article", "add_article", "change_article",
        "view_category", "view_tag",
    ],
    "SEO Manager": [
        "view_article", "change_article",
        "view_category", "change_category",
        "view_tag", "add_tag", "change_tag",
        "view_webstory", "change_webstory",
    ],
    "Ads Manager": [
        "view_advertisement", "add_advertisement", "change_advertisement", "delete_advertisement",
    ],
    "Media Manager": [
        "view_gallery", "add_gallery", "change_gallery", "delete_gallery",
        "view_galleryimage", "add_galleryimage", "change_galleryimage", "delete_galleryimage",
        "view_video", "add_video", "change_video", "delete_video",
        "view_webstory", "add_webstory", "change_webstory", "delete_webstory",
        "view_storyslide", "add_storyslide", "change_storyslide", "delete_storyslide",
    ],
    "Live Desk": [
        "view_liveblog", "add_liveblog", "change_liveblog", "delete_liveblog",
        "view_liveupdate", "add_liveupdate", "change_liveupdate", "delete_liveupdate",
        "view_article", "change_article",
    ],
}


class Command(BaseCommand):
    help = "Create role groups and assign permissions for the smart portal."

    def handle(self, *args, **options):
        permission_map = {permission.codename: permission for permission in Permission.objects.all()}
        for role, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            group.permissions.clear()
            for codename in codenames:
                permission = permission_map.get(codename)
                if permission:
                    group.permissions.add(permission)

        admin = User.objects.filter(is_superuser=True).first()
        if admin:
            admin.groups.add(Group.objects.get(name="Admin"))

        self.stdout.write(self.style.SUCCESS("Smart portal roles and permissions are ready."))
