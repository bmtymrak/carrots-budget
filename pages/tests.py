from urllib.parse import parse_qs, urlsplit

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.template.loader import render_to_string
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse


class HomePageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "A-test-password-for-landing"
        cls.user = get_user_model().objects.create_user(
            username="landing-user", email="landing@example.com", password=cls.password
        )
        EmailAddress.objects.create(
            user=cls.user, email=cls.user.email, primary=True, verified=True
        )

    def setUp(self):
        cache.clear()

    def credentials(self, **extra):
        return {"login": self.user.email, "password": self.password, **extra}

    def test_homepage(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertTemplateUsed(response, "_includes/landing_login.html")
        self.assertContains(response, 'action="/accounts/login/"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'type="email" name="login"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertContains(response, '<label for="id_login">Email</label>', html=True)
        self.assertNotContains(response, "Email or username")
        self.assertContains(response, "images/carrots_logo.svg")
        self.assertContains(response, "images/landing/monthly-budget-preview.webp")
        self.assertContains(response, reverse("account_signup"))
        self.assertContains(response, reverse("account_reset_password"))
        self.assertContains(response, 'name="remember"')
        self.assertIn("no-store", response["Cache-Control"])

    def test_account_login_uses_same_landing_page(self):
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "_includes/landing_login.html")
        self.assertContains(response, "Your whole budget, without the noise.")

    def test_authenticated_home_redirects_to_yearly_budgets(self):
        self.client.force_login(self.user)
        for method in (self.client.get, self.client.post):
            with self.subTest(method=method.__name__):
                response = method(reverse("home"), {"next": reverse("account_email")})
                self.assertRedirects(
                    response, reverse("yearly_list"), fetch_redirect_response=False
                )

    def test_valid_login_uses_allauth_from_either_endpoint(self):
        for route in ("home", "account_login"):
            with self.subTest(route=route):
                client = Client()
                response = client.post(reverse(route), self.credentials())
                self.assertRedirects(
                    response, reverse("yearly_list"), fetch_redirect_response=False
                )
                self.assertEqual(int(client.session["_auth_user_id"]), self.user.pk)
                self.assertTrue(client.session.get_expire_at_browser_close())

    def test_remember_me_preserves_persistent_session(self):
        response = self.client.post(
            reverse("account_login"), self.credentials(remember="on")
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    @override_settings(ACCOUNT_SESSION_REMEMBER=True)
    def test_forced_remember_setting_does_not_render_missing_field(self):
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, 'name="remember"')
        response = self.client.post(reverse("home"), self.credentials())
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_bad_credentials_keep_design_email_and_next_but_not_password(self):
        for route in ("home", "account_login"):
            with self.subTest(route=route):
                response = self.client.post(
                    reverse(route),
                    self.credentials(
                        password="incorrect-password", next="/budgets/", remember="on"
                    ),
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].non_field_errors())
                self.assertTemplateUsed(response, "_includes/landing_login.html")
                self.assertContains(response, 'value="landing@example.com"')
                self.assertContains(response, 'name="next" value="/budgets/"')
                self.assertContains(response, 'role="alert"')
                self.assertTrue(response.context["form"]["remember"].value())
                self.assertNotContains(response, "incorrect-password")
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_required_field_errors_are_rendered_and_associated(self):
        response = self.client.post(reverse("account_login"), {})
        self.assertEqual(response.status_code, 200)
        self.assertIn("login", response.context["form"].errors)
        self.assertIn("password", response.context["form"].errors)
        self.assertContains(response, 'id="id_login_error"')
        self.assertContains(response, 'aria-describedby="id_login_error"')
        self.assertContains(response, 'id="id_password_error"')
        self.assertContains(response, 'id="id_password_helptext"')
        self.assertContains(response, 'aria-invalid="true"', count=2)

    def test_email_only_authentication_does_not_accept_a_username(self):
        response = self.client.post(
            reverse("home"), self.credentials(login=self.user.username)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("login", response.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_next_is_retained_on_get_and_used_after_login(self):
        target = reverse("account_email")
        response = self.client.get(reverse("home"), {"next": target})
        self.assertContains(response, f'name="next" value="{target}"')
        signup_url = response.context["signup_url"]
        self.assertEqual(urlsplit(signup_url).path, reverse("account_signup"))
        self.assertEqual(parse_qs(urlsplit(signup_url).query), {"next": [target]})
        self.assertContains(response, signup_url)
        response = self.client.post(
            reverse("account_login"), self.credentials(next=target)
        )
        self.assertRedirects(response, target, fetch_redirect_response=False)

    def test_external_next_cannot_create_an_open_redirect(self):
        for target in ("https://example.net/steal", "//example.net/steal"):
            with self.subTest(target=target):
                client = Client()
                response = client.post(
                    reverse("home"), self.credentials(next=target)
                )
                self.assertRedirects(
                    response, reverse("yearly_list"), fetch_redirect_response=False
                )

    def test_form_values_and_errors_are_escaped(self):
        malicious = '\"><script>alert("landing")</script>'
        response = self.client.post(
            reverse("home"), {"login": malicious, "next": malicious}
        )
        self.assertNotContains(response, "<script>alert(")
        self.assertContains(response, "&lt;script&gt;")
        form = response.context["form"]
        form.add_error(None, malicious)
        markup = render_to_string("_includes/landing_login.html", {"form": form})
        self.assertNotIn("<script>alert(", markup)
        self.assertIn("&lt;script&gt;", markup)

    def test_both_login_endpoints_require_csrf(self):
        for route in ("home", "account_login"):
            with self.subTest(route=route):
                client = Client(enforce_csrf_checks=True)
                response = client.post(reverse(route), self.credentials())
                self.assertEqual(response.status_code, 403)
                client.get(reverse("home"))
                token = client.cookies["csrftoken"].value
                response = client.post(
                    reverse(route), self.credentials(csrfmiddlewaretoken=token)
                )
                self.assertRedirects(
                    response, reverse("yearly_list"), fetch_redirect_response=False
                )

    def test_other_public_pages_do_not_load_landing_assets(self):
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "css/landing.css")
        self.assertNotContains(response, "js/app/pages/landing.js")


class SharedFrontendComponentTests(SimpleTestCase):
    def test_icon_action_renders_semantic_button_and_link_variants(self):
        context = {
            "action_label": "Edit purchase",
            "action_url": "/purchases/1/edit/",
            "icon_path": "images/edit-pencil.svg",
        }

        button_markup = render_to_string("_includes/icon_action.html", context)
        link_markup = render_to_string(
            "_includes/icon_action.html", {**context, "element": "link"}
        )

        self.assertIn(
            '<button class="button-blank icon-action" type="button"', button_markup
        )
        self.assertIn('aria-label="Edit purchase"', button_markup)
        self.assertIn('<a class="button-blank icon-action"', link_markup)
        self.assertIn('aria-label="Edit purchase"', link_markup)
        self.assertIn('href="/purchases/1/edit/"', link_markup)

    def test_modal_shell_renders_native_dialog_and_close_control(self):
        modal_markup = render_to_string("_includes/modal_shell.html")

        self.assertIn('<dialog id="modal"', modal_markup)
        self.assertIn('closedby="any"', modal_markup)
        self.assertIn('method="dialog"', modal_markup)
        self.assertIn('aria-label="Close dialog"', modal_markup)
