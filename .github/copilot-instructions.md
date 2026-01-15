# Copilot Instructions for Carrots Budget

## Project Overview

Carrots Budgeting is a personal finance web application for budgeting and spending tracking built with Django. It's designed to replace spreadsheet-based budgeting systems with features that streamline budgeting and spending tracking while providing flexibility to match different budgeting strategies.

## Tech Stack

- **Backend**: Django 5.2+ / Python 3.11+
- **Frontend**: Django templates with HTMX for interactivity, vanilla JavaScript
- **Database**: PostgreSQL (production), SQLite (development)
- **Authentication**: django-allauth
- **Package Manager**: uv (modern Python package manager)
- **Static Files**: WhiteNoise for serving static files
- **CSS**: Custom CSS (no framework)

## Project Structure

```
carrots-budget/
├── accounts/       # User account management
├── budgets/        # Budget models, views, and logic
├── purchases/      # Purchase and income tracking
├── pages/          # General pages (home, etc.)
├── project/        # Django project settings
├── templates/      # Django templates
│   ├── _base.html
│   ├── budgets/
│   ├── purchases/
│   └── account/
├── static/         # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── images/
└── manage.py
```

## Development Setup

### Installing Dependencies

Use `uv` to manage Python dependencies:

```bash
uv sync
```

### Running the Development Server

```bash
uv run python manage.py runserver
```

### Database Migrations

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## Testing

### Running Tests

Run all tests:
```bash
uv run python manage.py test
```

Run tests for a specific app:
```bash
uv run python manage.py test budgets
uv run python manage.py test purchases
uv run python manage.py test accounts
```

Run a specific test class or method:
```bash
uv run python manage.py test budgets.tests.test_models.TestYearlyBudget
uv run python manage.py test budgets.tests.test_models.TestYearlyBudget.test_monthly_budgets_created
```

### Testing Conventions

- Tests are located in each app's `tests/` directory or `tests.py` file
- Use Django's `TestCase` class for database-dependent tests
- Use `setUpTestData()` for test data that doesn't change across test methods
- Use factory-boy for creating test data (available as dev dependency)
- Test files follow the pattern: `test_models.py`, `test_views.py`, `test_forms.py`

## Coding Conventions

### Python/Django Style

- Follow Django's coding style guidelines
- Use double quotes for strings consistently
- Imports order: standard library, third-party packages, Django imports, local imports
- Use Django class-based views (CBVs) for standard CRUD operations
- Use function-based views when more control is needed
- Use mixins for reusable view functionality (see `AddUserMixin` in views)

### Models

- Always include `__str__()` method for models
- Use `related_name` for foreign keys to improve query readability
- Use `Meta` class for model options (ordering, constraints, etc.)
- Add unique constraints at the database level when needed
- Use `settings.AUTH_USER_MODEL` for foreign keys to User model

### Views

- Use `LoginRequiredMixin` for views requiring authentication
- Inherit from appropriate generic views (ListView, CreateView, DetailView, etc.)
- Override `form_valid()` to add custom form processing logic
- Use `context_object_name` to make templates more readable
- Use Django's URL reversal (`reverse`, `reverse_lazy`) instead of hardcoded URLs

### Templates

- Extend from `_base.html` for consistent layout
- Use `{% load static %}` for static file references
- Use HTMX attributes (`hx-get`, `hx-post`, etc.) for dynamic interactions
- Include CSRF token in HTMX headers: `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'`
- Keep JavaScript minimal and in separate files in `static/js/`

### Forms

- Create ModelForms for database models
- Use formsets when working with multiple related objects
- Add custom validation in `clean()` or `clean_<field>()` methods
- Use widgets to customize form field rendering

## Key Features & Patterns

### Budget Management

- `YearlyBudget` automatically creates 12 `MonthlyBudget` instances when saved
- Budget items can be assigned to specific months or spread across the year
- Rollover functionality allows unused budget to carry forward

### User Isolation

- All models are scoped to users via `ForeignKey` to `AUTH_USER_MODEL`
- Views use `LoginRequiredMixin` to ensure authentication
- QuerySets are filtered by `request.user` to ensure data isolation

### HTMX Integration

- HTMX is used for dynamic page updates without full page reloads
- HTMX middleware is included in the middleware stack
- Use `HttpResponseClientRedirect` from `django_htmx.http` for HTMX redirects
- CSRF token is passed in HTMX headers via the base template

### Services Layer

- Business logic is separated into service modules (e.g., `budgets/services.py`)
- Use `BudgetService` for complex budget calculations and operations
- Keep views thin by delegating to service classes

## Common Tasks

### Adding a New Model

1. Define the model in the appropriate app's `models.py`
2. Include `user` ForeignKey for multi-user support
3. Add `__str__()` method and Meta class
4. Create and run migrations: `uv run python manage.py makemigrations && uv run python manage.py migrate`
5. Register in admin.py if needed
6. Add tests in `tests/test_models.py`

### Adding a New View

1. Create the view in `views.py` using appropriate base class
2. Add URL pattern in the app's `urls.py`
3. Create template in `templates/<app_name>/`
4. Add tests in `tests/test_views.py`
5. Ensure proper authentication and user isolation

### Adding a New Form

1. Create ModelForm or Form in `forms.py`
2. Add custom validation if needed
3. Use in views (CreateView, UpdateView, or custom views)
4. Add tests in `tests/test_forms.py`

## Security Considerations

- All user data must be scoped to the authenticated user
- Use Django's CSRF protection (enabled by default)
- Never commit `.env` file or secrets (already in `.gitignore`)
- Use environment variables for sensitive configuration
- Validate and sanitize all user inputs
- Use Django's built-in protection against SQL injection, XSS, and CSRF

## Dependencies

Key dependencies and their purposes:

- `django-allauth`: User authentication and account management
- `django-environ`: Environment variable management and configuration
- `django-htmx`: HTMX integration for Django
- `django-extensions`: Additional Django management commands
- `django-debug-toolbar`: Development debugging
- `whitenoise`: Efficient static file serving
- `psycopg2-binary`: PostgreSQL database adapter
- `factory-boy`: Test data generation (dev dependency)

## Environment Variables

Required environment variables (stored in `.env`, not committed):

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- Database configuration (for production)

## Notes for AI Assistants

- This project uses `uv` instead of pip for package management
- Tests should always use `TestCase` from Django for database interactions
- When adding new features, follow the existing patterns in similar apps
- Keep the service layer separate from views for complex business logic
- Maintain user data isolation by always filtering by `request.user`
- Use HTMX for interactive features rather than introducing heavy JavaScript frameworks
- Follow Django's conventions for file organization and naming
