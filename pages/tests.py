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

    def test_template_images_define_alternative_text(self):
        for template_name, source in self.template_sources():
            with self.subTest(template=template_name):
                for image in re.findall(r"<img\b[^>]*>", source):
                    self.assertRegex(image, r"\balt=(['\"]).*?\1")
                    self.assertNotRegex(image, r'\bwidth="\d+px"')

    def test_icon_action_buttons_are_explicitly_labelled(self):
        for template_name, source in self.template_sources():
            with self.subTest(template=template_name):
                for line in source.splitlines():
                    if 'class="button-blank"' in line:
                        self.assertIn('type="button"', line)
                        self.assertIn("aria-label=", line)
                    if 'class="list-nav-icon"' in line:
                        self.assertIn('alt=""', line)
                        self.assertIn('aria-hidden="true"', line)
