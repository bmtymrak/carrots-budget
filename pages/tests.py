import re

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class HomePageTest(TestCase):
    def test_homepage(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")


class FrontendTemplateMarkupTests(SimpleTestCase):
    def template_sources(self):
        template_root = settings.BASE_DIR / "templates"
        for template_path in sorted(template_root.rglob("*.html")):
            yield template_path.relative_to(template_root), template_path.read_text()

    def test_templates_avoid_known_invalid_action_markup(self):
        for template_name, source in self.template_sources():
            with self.subTest(template=template_name):
                self.assertNotIn("href=''", source)
                self.assertNotIn('href=""', source)
                for line in source.splitlines():
                    if "<button" in line:
                        self.assertNotIn("</a>", line)

    def test_templates_do_not_use_empty_class_attributes(self):
        for template_name, source in self.template_sources():
            with self.subTest(template=template_name):
                self.assertNotRegex(source, r"\bclass=(['\"])\s*\1")

    def test_template_images_define_alternative_text(self):
        for template_name, source in self.template_sources():
            with self.subTest(template=template_name):
                for image in re.findall(r"<img\b[^>]*>", source):
                    self.assertRegex(image, r"\balt=(['\"]).*?\1")
                    self.assertNotRegex(image, r'\bwidth="\d+px"')

    def test_icon_action_controls_are_explicitly_labelled(self):
        for template_name, source in self.template_sources():
            with self.subTest(template=template_name):
                for line in source.splitlines():
                    if 'class="button-blank"' in line:
                        self.assertIn("aria-label=", line)
                        if "<button" in line:
                            self.assertIn('type="button"', line)
                        if "<a" in line:
                            self.assertIn("href=", line)
                    if 'class="list-nav-icon"' in line:
                        self.assertIn('alt=""', line)
                        self.assertIn('aria-hidden="true"', line)

    def test_modal_shell_has_dialog_and_close_semantics(self):
        modal_shell = (
            settings.BASE_DIR / "templates/_includes/modal_shell.html"
        ).read_text()

        self.assertIn('<dialog id="modal"', modal_shell)
        self.assertIn('aria-label="Dialog"', modal_shell)
        self.assertIn('closedby="any"', modal_shell)
        self.assertNotIn('class="overlay', modal_shell)
        self.assertIn('method="dialog"', modal_shell)
        self.assertIn('aria-label="Close dialog"', modal_shell)
