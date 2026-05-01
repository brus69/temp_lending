from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("category/", views.category, name="category"),
    path("sub-category/", views.sub_category, name="sub_category"),
    path("sub-category/<slug:slug>/", views.sub_category, name="sub_category_by_slug"),
    path("product-detail/", views.product_detail, name="product_detail"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_page, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("quick-order/<int:product_id>/", views.quick_order, name="quick_order"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/success/<int:order_id>/", views.checkout_success, name="checkout_success"),
    path("search/", views.search, name="search"),
    path("account/", views.account, name="account"),
]
