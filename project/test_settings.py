"""Settings used when running the automated test suite."""

from .settings import *  # noqa: F403


# Password strength is production behavior, not part of most application tests.
# Using a fast hasher keeps user creation and login from dominating suite runtime.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


# Template tests should not depend on a previously generated production asset
# manifest. Manifest generation belongs in a separate collectstatic check.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}
