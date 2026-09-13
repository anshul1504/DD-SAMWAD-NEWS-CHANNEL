"""Shared cache-backed rate limiting.

The OTP flow's throttle was the project's first implementation of this; it is
generalised here so abuse-prone public endpoints (contact form, OTP requests)
share one mechanism instead of drifting apart. Backed by the configured cache,
which is deliberately Redis or the database table rather than per-process
LocMemCache so limits cannot be bypassed by hitting a different worker.
"""

from django.core.cache import cache


def client_ip(request, default=None):
    """Best-effort client IP.

    The rightmost X-Forwarded-For entry is the hop appended by our own trusted
    proxy; the leftmost value is client-supplied and can be spoofed, so it must
    never be used for rate limiting.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR") or default


def peek_rate_limit(scope, rules, cooldown=None):
    """Return the first exceeded rule's message without consuming any quota.

    Use this when the event being limited is a *failure* (a wrong password, say)
    rather than the request itself: check before acting, then call
    ``consume_rate_limit`` only when the attempt actually fails, so legitimate
    users are never throttled for succeeding.
    """
    if cooldown:
        identifier, _seconds, message = cooldown
        if cache.get(f"{scope}:{identifier}"):
            return message

    for identifier, limit, _window, message in rules:
        if int(cache.get(f"{scope}:{identifier}") or 0) >= limit:
            return message
    return ""


def consume_rate_limit(scope, rules, cooldown=None):
    """Increment each rule's counter, and arm the cooldown when given."""
    if cooldown:
        identifier, seconds, _message = cooldown
        cache.set(f"{scope}:{identifier}", True, seconds)
    for identifier, _limit, window, _message in rules:
        key = f"{scope}:{identifier}"
        cache.set(key, int(cache.get(key) or 0) + 1, window)


def check_rate_limit(scope, rules, cooldown=None):
    """Return an error message when throttled, or "" when the caller may proceed.

    ``rules`` is an iterable of ``(identifier, limit, window_seconds, message)``.
    ``cooldown`` is an optional ``(identifier, seconds, message)`` guard against
    rapid repeat requests.

    Quota is consumed only when the request is allowed, so a caller that is
    already blocked does not extend its own lockout.
    """
    rules = list(rules)
    blocked = peek_rate_limit(scope, rules, cooldown)
    if blocked:
        return blocked
    consume_rate_limit(scope, rules, cooldown)
    return ""
