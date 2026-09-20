"""Shared validation for application-owned return destinations."""

import unicodedata
from urllib.parse import urlsplit

from django.utils.http import url_has_allowed_host_and_scheme


def safe_next_url(request, *, fallback, allowed_paths=None):
    """Use POST's explicit choice (even blank), otherwise the query string.

    Destinations must use the request host, including its port. HTTP requests
    may return to HTTPS; HTTPS requests cannot downgrade to HTTP. Callers may
    additionally restrict exact paths without discarding query strings.
    """
    def validated_url(value):
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value or any(unicodedata.category(char) == 'Cc' for char in value):
            return None
        if not url_has_allowed_host_and_scheme(
            value,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return None
        return value

    fallback = validated_url(str(fallback) if fallback is not None else None)
    if fallback is None:
        raise ValueError('A trusted, non-empty fallback URL is required.')

    submitted_url = request.POST.get('next') if 'next' in request.POST else request.GET.get('next')
    next_url = validated_url(submitted_url)
    if next_url is not None and (
        allowed_paths is None or urlsplit(next_url).path in allowed_paths
    ):
        return next_url
    return fallback
