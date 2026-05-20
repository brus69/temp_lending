from django.test import TestCase

from shop.html_sanitize import sanitize_html
from shop.models import Article, TopMenuLink
from shop.tests.factories import make_category, make_product


class HtmlSanitizeTests(TestCase):
    def test_strips_script_tags(self):
        dirty = '<p>Hello</p><script>alert("xss")</script>'
        self.assertEqual(sanitize_html(dirty), "<p>Hello</p>")

    def test_keeps_allowed_formatting(self):
        html = "<h2>Title</h2><p><strong>Bold</strong> and <a href=\"/info/test/\">link</a></p>"
        self.assertEqual(sanitize_html(html), html)

    def test_top_menu_link_sanitizes_on_save(self):
        page = TopMenuLink.objects.get(title="О нас")
        page.body = "<p>Safe</p><script>evil()</script>"
        page.save()
        page.refresh_from_db()
        self.assertEqual(page.body, "<p>Safe</p>")

    def test_article_sanitizes_on_save(self):
        article = Article.objects.first()
        article.body = "<ul><li>Item</li></ul><iframe src=\"evil\"></iframe>"
        article.save()
        article.refresh_from_db()
        self.assertEqual(article.body, "<ul><li>Item</li></ul>")

    def test_product_description_sanitizes_on_save(self):
        product = make_product(
            category=make_category(),
            description="<p>Описание</p><script>evil()</script>",
        )
        product.refresh_from_db()
        self.assertEqual(product.description, "<p>Описание</p>")
