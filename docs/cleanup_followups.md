# Cleanup Follow-ups

- Test suite currently fails with `Missing staticfiles manifest entry` errors because ManifestStaticFilesStorage expects collected assets. Add a test-specific staticfiles storage override (e.g., via `STORAGES["staticfiles"]` or similar) or incorporate a collectstatic step for tests to unblock running the suite.
- Running tests locally requires setting `SECRET_KEY`, `ALLOWED_HOSTS`, and `ENVIRONMENT`; consider adding test defaults or a dedicated settings module to streamline setup.
