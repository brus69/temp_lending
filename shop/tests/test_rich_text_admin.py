from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from django_ckeditor_5.widgets import CKEditor5Widget

from shop.admin import ArticleAdmin, ProductAdmin, TopMenuLinkAdmin
from shop.models import Article, Product, TopMenuLink


class RichTextAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.request = RequestFactory().get("/admin/")

    def test_top_menu_admin_uses_ckeditor_for_body(self):
        admin = TopMenuLinkAdmin(TopMenuLink, self.site)
        form = admin.get_form(self.request)()
        self.assertIsInstance(form.fields["body"].widget, CKEditor5Widget)

    def test_article_admin_uses_ckeditor_for_body(self):
        admin = ArticleAdmin(Article, self.site)
        form = admin.get_form(self.request)()
        self.assertIsInstance(form.fields["body"].widget, CKEditor5Widget)

    def test_product_admin_uses_ckeditor_for_description(self):
        admin = ProductAdmin(Product, self.site)
        form = admin.get_form(self.request)()
        self.assertIsInstance(form.fields["description"].widget, CKEditor5Widget)
