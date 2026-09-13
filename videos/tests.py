import json

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Video, VideoComment, VideoLike, youtube_embed_url


class YouTubeEmbedUrlTests(TestCase):
    """The detail template fed youtube_url straight into an iframe. Only the
    /embed/ form can be framed — a watch URL is refused by YouTube's frame
    policy and renders as a blank player with no error message."""

    def test_watch_url_is_converted(self):
        self.assertEqual(
            youtube_embed_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        )

    def test_short_link_is_converted(self):
        self.assertEqual(
            youtube_embed_url("https://youtu.be/dQw4w9WgXcQ"),
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        )

    def test_shorts_and_live_urls_are_converted(self):
        for url in ("https://www.youtube.com/shorts/dQw4w9WgXcQ",
                    "https://www.youtube.com/live/dQw4w9WgXcQ"):
            with self.subTest(url=url):
                self.assertEqual(youtube_embed_url(url),
                                 "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")

    def test_mobile_url_with_timestamp_is_converted(self):
        self.assertEqual(
            youtube_embed_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=30s"),
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        )

    def test_already_embeddable_url_is_preserved(self):
        self.assertEqual(
            youtube_embed_url("https://www.youtube.com/embed/dQw4w9WgXcQ"),
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        )

    def test_non_youtube_and_malformed_urls_are_rejected(self):
        for url in ("https://vimeo.com/12345", "not a url", "", None,
                    "https://www.youtube.com/watch?v=<script>"):
            with self.subTest(url=url):
                self.assertEqual(youtube_embed_url(url), "")

    def test_url_missing_scheme_is_still_converted(self):
        """Non-technical editors often paste a link straight from the address
        bar without "https://" -- that must not silently fail."""
        for url in ("youtube.com/watch?v=dQw4w9WgXcQ", "youtu.be/dQw4w9WgXcQ",
                    "www.youtube.com/shorts/dQw4w9WgXcQ"):
            with self.subTest(url=url):
                self.assertEqual(youtube_embed_url(url),
                                  "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")

    def test_bare_video_id_is_accepted(self):
        """A client who copies just the id out of the middle of a share link
        (no youtube.com/youtu.be around it at all) should still work."""
        self.assertEqual(
            youtube_embed_url("dQw4w9WgXcQ"),
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        )

    def test_share_link_with_tracking_params_is_converted(self):
        """The real-world mobile share-sheet link that started this: a Shorts
        URL with a "?si=" tracking parameter appended."""
        self.assertEqual(
            youtube_embed_url("https://youtube.com/shorts/dQw4w9WgXcQ?si=FBACjdfS-t9-3iKv"),
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        )


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class VideoDetailTests(TestCase):
    def test_playable_video_renders_an_iframe(self):
        video = Video.objects.create(
            title="Playable", slug="playable",
            youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", active=True,
        )
        body = self.client.get(video.get_absolute_url()).content.decode()
        self.assertIn("youtube-nocookie.com/embed/dQw4w9WgXcQ", body)
        self.assertIn("<iframe", body)

    def test_unplayable_video_shows_a_fallback_not_a_blank_player(self):
        video = Video.objects.create(
            title="Unplayable", slug="unplayable",
            youtube_url="https://vimeo.com/12345", active=True,
        )
        body = self.client.get(video.get_absolute_url()).content.decode()
        self.assertNotIn("<iframe", body)
        self.assertIn("video-unavailable", body)
        self.assertIn("https://vimeo.com/12345", body)

    def test_shorts_reels_viewer_uses_a_placeholder_div_not_an_iframe(self):
        """The YouTube IFrame Player API's documented contract is to replace
        a placeholder <div>/<span>, not take over an existing <iframe> --
        targeting an iframe directly caused every video after the first to
        silently fail to bind, since Player#destroy() removes that element
        from the DOM and a later `new YT.Player(detachedIframe, ...)` call
        can't attach to anything. Locks in the fix: the reels frame must be
        a plain <div data-reels-frame>, and the JS builds the real <iframe>."""
        video = Video.objects.create(
            title="Short", slug="short-reel", is_short=True,
            youtube_url="https://youtu.be/dQw4w9WgXcQ", active=True,
        )
        body = self.client.get(video.get_absolute_url()).content.decode()
        self.assertIn("data-reels-frame", body)
        self.assertNotIn("<iframe", body)

    def test_view_counter_still_increments(self):
        video = Video.objects.create(
            title="Counted", slug="counted",
            youtube_url="https://youtu.be/dQw4w9WgXcQ", active=True,
        )
        self.client.get(video.get_absolute_url())
        video.refresh_from_db()
        self.assertEqual(video.views, 1)

    def test_feed_includes_comment_urls_for_reels_js(self):
        video = Video.objects.create(
            title="Feed item", slug="feed-item",
            youtube_url="https://youtu.be/dQw4w9WgXcQ", active=True,
        )
        body = self.client.get(video.get_absolute_url()).content.decode()
        self.assertIn(reverse("videos:comments", args=[video.slug]), body)
        self.assertIn(reverse("videos:comment_create", args=[video.slug]), body)
        self.assertIn(reverse("videos:view_increment", args=[video.slug]), body)

    def test_list_page_inline_player_uses_a_placeholder_div_not_an_iframe(self):
        """Same fix as the reels viewer, for the desktop inline player on the
        /videos/ grid: the target must be a <div>, not an <iframe>."""
        Video.objects.create(
            title="Long form", slug="long-form",
            youtube_url="https://youtu.be/dQw4w9WgXcQ", active=True,
        )
        body = self.client.get(reverse("videos:list")).content.decode()
        self.assertIn("data-video-player-frame", body)
        self.assertNotIn("<iframe", body)

    def test_view_increment_endpoint_counts_swiped_reels(self):
        video = Video.objects.create(
            title="Swiped", slug="swiped",
            youtube_url="https://youtu.be/dQw4w9WgXcQ", active=True,
        )
        response = self.client.post(reverse("videos:view_increment", args=[video.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["views"], 1)

    def test_view_increment_endpoint_dedupes_rapid_repeat(self):
        video = Video.objects.create(
            title="Deduped", slug="deduped",
            youtube_url="https://youtu.be/dQw4w9WgXcQ", active=True,
        )
        url = reverse("videos:view_increment", args=[video.slug])
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 429)
        video.refresh_from_db()
        self.assertEqual(video.views, 1)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class VideoCommentEndpointTests(TestCase):
    def setUp(self):
        self.video = Video.objects.create(
            title="Commentable", slug="commentable",
            youtube_url="https://youtu.be/dQw4w9WgXcQ", active=True,
        )

    def test_list_returns_only_approved_comments(self):
        VideoComment.objects.create(video=self.video, name="A", text="visible", approved=True)
        VideoComment.objects.create(video=self.video, name="B", text="hidden", approved=False)
        response = self.client.get(reverse("videos:comments", args=[self.video.slug]))
        data = response.json()
        self.assertEqual(len(data["comments"]), 1)
        self.assertEqual(data["comments"][0]["text"], "visible")

    def test_create_comment_succeeds_and_increments_count(self):
        response = self.client.post(
            reverse("videos:comment_create", args=[self.video.slug]),
            data=json.dumps({"name": "Reader", "text": "Nice video"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["comment"]["name"], "Reader")
        self.assertEqual(data["comment_count"], 1)
        self.assertEqual(VideoComment.objects.count(), 1)

    def test_honeypot_field_rejects_bots(self):
        response = self.client.post(
            reverse("videos:comment_create", args=[self.video.slug]),
            data=json.dumps({"name": "Bot", "text": "spam", "website": "http://spam.example"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(VideoComment.objects.count(), 0)

    def test_missing_fields_are_rejected(self):
        response = self.client.post(
            reverse("videos:comment_create", args=[self.video.slug]),
            data=json.dumps({"name": "", "text": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rate_limit_blocks_rapid_repeat_submissions(self):
        url = reverse("videos:comment_create", args=[self.video.slug])
        first = self.client.post(url, data=json.dumps({"name": "R", "text": "one"}), content_type="application/json")
        second = self.client.post(url, data=json.dumps({"name": "R", "text": "two"}), content_type="application/json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class VideoLikeEndpointTests(TestCase):
    def setUp(self):
        self.video = Video.objects.create(
            title="Likeable", slug="likeable",
            youtube_url="https://youtu.be/dQw4w9WgXcQ", active=True,
        )

    def test_like_then_unlike_toggles_count(self):
        url = reverse("videos:like_toggle", args=[self.video.slug])
        first = self.client.post(url).json()
        self.assertTrue(first["liked"])
        self.assertEqual(first["likes"], 1)

        second = self.client.post(url).json()
        self.assertFalse(second["liked"])
        self.assertEqual(second["likes"], 0)
        self.assertEqual(VideoLike.objects.count(), 0)

    def test_feed_reports_liked_state_for_current_visitor(self):
        self.client.post(reverse("videos:like_toggle", args=[self.video.slug]))
        body = self.client.get(self.video.get_absolute_url()).content.decode()
        self.assertIn('"liked": true', body)
