from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class HomePageTest(TestCase):
    def test_homepage(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")


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

        self.assertIn('<button class="button-blank" type="button"', button_markup)
        self.assertIn('aria-label="Edit purchase"', button_markup)
        self.assertIn('<a class="button-blank"', link_markup)
        self.assertIn('aria-label="Edit purchase"', link_markup)
        self.assertIn('href="/purchases/1/edit/"', link_markup)

    def test_modal_shell_renders_native_dialog_and_close_control(self):
        modal_markup = render_to_string("_includes/modal_shell.html")

        self.assertIn('<dialog id="modal"', modal_markup)
        self.assertIn('closedby="any"', modal_markup)
        self.assertIn('method="dialog"', modal_markup)
        self.assertIn('aria-label="Close dialog"', modal_markup)
