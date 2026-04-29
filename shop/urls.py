from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("category/", views.category, name="category"),
    path("sub-category/", views.sub_category, name="sub_category"),
    path("sub-category/<slug:slug>/", views.sub_category, name="sub_category_by_slug"),
    path("product-detail/", views.product_detail, name="product_detail"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
]
