from django.test import TestCase

from shop.models import Article, News, Promotion


class ContentPagesTests(TestCase):
    def test_seed_migration_populates_ten_each(self):
        self.assertEqual(Article.objects.count(), 10)
        self.assertEqual(News.objects.count(), 10)
        self.assertEqual(Promotion.objects.count(), 10)

    def test_article_list_and_detail(self):
        article = Article.objects.first()
        list_response = self.client.get("/articles/")
        detail_response = self.client.get(f"/articles/{article.slug}/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(list_response, article.title)
        self.assertContains(detail_response, article.title)

    def test_footer_contains_content_links(self):
        article = Article.objects.first()
        response = self.client.get("/")
        self.assertContains(response, 'href="/articles/"')
        self.assertContains(response, f'href="/articles/{article.slug}/"')

    def test_homepage_has_content_carousels(self):
        news = News.objects.first()
        article = Article.objects.first()
        promotion = Promotion.objects.first()
        response = self.client.get("/")
        self.assertContains(response, "vi-content-carousel")
        self.assertContains(response, "Новости")
        self.assertContains(response, "Статьи")
        self.assertContains(response, "Акции")
        self.assertContains(response, f'href="/news/{news.slug}/"')
        self.assertContains(response, f'href="/articles/{article.slug}/"')
        self.assertContains(response, f'href="/promotions/{promotion.slug}/"')
        self.assertContains(response, "vi-home-content-card")

    def test_promotion_list_matches_card_layout(self):
        response = self.client.get("/promotions/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Промокоды, акции, скидки, купоны, конкурсы")
        self.assertContains(response, "Наши акции")
        self.assertContains(response, "vi-content-card-grid")
        self.assertContains(response, "vi-content-card__image")
        self.assertContains(response, "photo-1586864387967")
