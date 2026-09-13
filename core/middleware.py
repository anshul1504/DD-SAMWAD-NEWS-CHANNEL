from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string


class FriendlyMethodNotAllowedMiddleware:
    """Give 405 responses a real page.

    Django renders templates for 400/403/404/500, but a 405 from
    ``require_POST`` is an ``HttpResponseNotAllowed`` with an empty body — the
    browser shows a blank page. This is reachable in normal use (bookmarking is
    POST-only), so it gets the same treatment as the other error pages.

    The status code and Allow header are preserved; only the body is filled in.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            response.status_code == 405
            and not getattr(response, "streaming", False)
            and not response.content
            and "text/html" in request.META.get("HTTP_ACCEPT", "")
        ):
            try:
                response.content = render_to_string("405.html", request=request)
                response["Content-Type"] = "text/html; charset=utf-8"
            except TemplateDoesNotExist:
                pass
        return response
