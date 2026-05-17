from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("category/", views.category, name="category"),
    path("sub-category/", views.sub_category, name="sub_category"),
    path("sub-category/<slug:slug>/", views.sub_category, name="sub_category_by_slug"),
    path(
        "sub-category/<slug:slug>/filter-count/",
        views.sub_category_filter_count,
        name="sub_category_filter_count",
    ),
    path("product-detail/", views.product_detail, name="product_detail"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_page, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("favorites/toggle/<int:product_id>/", views.favorite_toggle, name="favorite_toggle"),
    path("quick-order/<int:product_id>/", views.quick_order, name="quick_order"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/success/<int:order_id>/", views.checkout_success, name="checkout_success"),
    path("search/", views.search, name="search"),
    path("account/", views.account, name="account"),
    path("account/favorites/", views.account_favorites, name="account_favorites"),
    path("account/orders/", views.account_orders, name="account_orders"),
    path("account/personal-data/", views.account_personal_data, name="account_personal_data"),
    path("account/personal-data/edit/", views.account_personal_data_edit, name="account_personal_data_edit"),
    path("account/password/", views.account_password_change, name="account_password_change"),
    path("account/organizations/", views.account_organizations, name="account_organizations"),
    path("auth/email-check/", views.auth_email_check, name="auth_email_check"),
    path("auth/login/", views.auth_login, name="auth_login"),
    path("auth/register/", views.auth_register, name="auth_register"),
    path("auth/confirm/<path:token>/", views.auth_confirm_email, name="auth_confirm_email"),
    path("auth/logout/", views.auth_logout, name="auth_logout"),
]
