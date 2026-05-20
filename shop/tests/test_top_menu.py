from django.test import TestCase

from shop.context_processors import header_top_menu_context
from shop.models import TopMenuLink


class TopMenuLinkTests(TestCase):
    def test_seed_creates_default_pages(self):
        titles = list(TopMenuLink.objects.order_by("sort_order").values_list("title", flat=True))
        self.assertEqual(
            titles,
            ["Получение и оплата", "Сервис и поддержка", "О нас"],
        )
        page = TopMenuLink.objects.get(title="О нас")
        self.assertEqual(page.slug, "o-nas")
        self.assertIn("<p>", page.body)

    def test_header_links_to_info_pages(self):
        page = TopMenuLink.objects.get(title="Получение и оплата")
        response = self.client.get("/")
        self.assertContains(response, f'href="/info/{page.slug}/"')
        self.assertContains(response, "Получение и оплата")

    def test_info_page_renders_content_and_seo(self):
        page = TopMenuLink.objects.get(title="О нас")
        page.meta_title = "О компании — магазин"
        page.meta_description = "История и контакты компании"
        page.body = "<p>Мы работаем с 2010 года.</p>"
        page.save()
        response = self.client.get(f"/info/{page.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "О компании — магазин")
        self.assertContains(response, 'name="description" content="История и контакты компании"')
        self.assertContains(response, "Мы работаем с 2010 года.")

    def test_inactive_page_hidden_from_menu_and_returns_404(self):
        page = TopMenuLink.objects.get(title="Сервис и поддержка")
        page.is_active = False
        page.save(update_fields=["is_active"])
        response = self.client.get("/")
        self.assertNotContains(response, f'href="/info/{page.slug}/"')
        self.assertNotContains(response, '<span class="vi-top-link">Сервис и поддержка</span>')
        self.assertEqual(self.client.get(f"/info/{page.slug}/").status_code, 404)

    def test_context_processor_returns_only_active(self):
        TopMenuLink.objects.filter(title="Сервис и поддержка").update(is_active=False)
        links = header_top_menu_context(None)["header_top_links"]
        self.assertEqual([link.title for link in links], ["Получение и оплата", "О нас"])
