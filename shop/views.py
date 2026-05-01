from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from .cart import add_to_cart, build_cart_items, clear_cart, remove_from_cart, set_quantity
from .models import Category, Favorite, Order, OrderItem, Organization, Product, UserProfile

EMAIL_CONFIRM_MAX_AGE_SECONDS = 60 * 60 * 24


def _build_email_confirmation_token(user: User) -> str:
    signer = TimestampSigner(salt="shop-email-confirm")
    return signer.sign(f"{user.id}:{user.email}")


def _parse_email_confirmation_token(token: str) -> User | None:
    signer = TimestampSigner(salt="shop-email-confirm")
    try:
        raw = signer.unsign(token, max_age=EMAIL_CONFIRM_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    try:
        user_id_str, email = raw.split(":", 1)
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return None
    return User.objects.filter(id=user_id, email__iexact=email).first()


def _send_confirmation_email(request, user: User) -> None:
    token = _build_email_confirmation_token(user)
    confirm_path = reverse("auth_confirm_email", args=[token])
    confirm_url = request.build_absolute_uri(confirm_path)
    send_mail(
        subject="Подтверждение email в LendingStore",
        message=(
            f"Здравствуйте!\n\n"
            f"Чтобы завершить регистрацию, подтвердите email по ссылке:\n{confirm_url}\n\n"
            f"Ссылка действует 24 часа."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )


def _seed_demo_data() -> None:
    if Category.objects.exists():
        return

    categories_data = [
        ("Метизы", "metizy", 438150, "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=260&q=80"),
        ("Скобяные изделия и фурнитура", "furnitura", 104522, "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?auto=format&fit=crop&w=260&q=80"),
        ("Специальный крепеж", "special-krepezh", 96788, "https://images.unsplash.com/photo-1599948128020-9a44505b3a80?auto=format&fit=crop&w=260&q=80"),
        ("Такелаж", "takelazh", 64732, "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=260&q=80"),
        ("Пластиковый крепеж", "plastic-krepezh", 28878, "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?auto=format&fit=crop&w=260&q=80"),
        ("Автомобильный крепеж", "auto-krepezh", 5246, "https://images.unsplash.com/photo-1611835151646-5a9df7f11463?auto=format&fit=crop&w=260&q=80"),
        ("Монтажные ленты", "montazhnye-lenty", 17715, "https://images.unsplash.com/photo-1585298723682-7115561c51b7?auto=format&fit=crop&w=260&q=80"),
        ("Химический", "chemical", 13699, "https://images.unsplash.com/photo-1620432468734-65f36cf65dfa?auto=format&fit=crop&w=260&q=80"),
    ]
    categories = []
    for idx, (name, slug, count, image_url) in enumerate(categories_data, start=1):
        categories.append(
            Category.objects.create(
                name=name,
                slug=slug,
                product_count=count,
                image_url=image_url,
                sort_order=idx,
            )
        )

    metizy = categories[0]
    products_data = [
        ("Гайка DIN934 оцинкованная M10 50 шт", "gaika-din934-m10", "SKU-015361", Decimal("210.00"), Decimal("358.00"), "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=1200&q=80"),
        ("Шайба DIN9021 кузовная M8 100 шт", "shaiba-din9021-m8", "SKU-015362", Decimal("270.00"), Decimal("377.00"), "https://images.unsplash.com/photo-1616789079464-9274d77b2d1f?auto=format&fit=crop&w=700&q=80"),
        ("Гайка DIN934 оцинкованная M8 100 шт", "gaika-din934-m8", "SKU-015363", Decimal("191.00"), Decimal("314.00"), "https://images.unsplash.com/photo-1616788494707-ec28f08d05a1?auto=format&fit=crop&w=700&q=80"),
        ("Шпилька резьбовая DIN975", "shpilka-din975", "SKU-015364", Decimal("71.00"), Decimal("154.00"), "https://images.unsplash.com/photo-1609942072337-c3370e820d25?auto=format&fit=crop&w=700&q=80"),
    ]

    for name, slug, sku, price, old_price, image_url in products_data:
        Product.objects.create(
            category=metizy,
            name=name,
            slug=slug,
            sku=sku,
            price=price,
            old_price=old_price,
            image_url=image_url,
            description="Надежный крепеж для строительных и монтажных задач.",
            specs={
                "Диаметр резьбы": "M10",
                "Шаг резьбы": "1.5",
                "Направление резьбы": "правая",
                "Размер под ключ": "17 мм",
                "Фасовка": "50 шт",
                "DIN": "934",
                "Материал": "сталь",
                "Покрытие": "цинк",
            },
            reviews_count=88,
            stock_store=120,
            stock_warehouse=260,
        )


def index(request):
    _seed_demo_data()
    categories = Category.objects.filter(is_featured=True)[:6]
    promo_products = Product.objects.all()[:4]
    return render(request, "shop/index.html", {"categories": categories, "promo_products": promo_products})


def category(request):
    _seed_demo_data()
    categories = Category.objects.filter(is_featured=True)
    return render(request, "shop/category.html", {"categories": categories})


def sub_category(request, slug=None):
    _seed_demo_data()
    categories = Category.objects.filter(is_featured=True)
    current_category = Category.objects.filter(slug=slug).first() if slug else categories.first()
    products = Product.objects.filter(category=current_category) if current_category else Product.objects.none()
    return render(
        request,
        "shop/sub_category.html",
        {"categories": categories, "current_category": current_category, "products": products},
    )


def product_detail(request, slug=None):
    _seed_demo_data()
    if not slug:
        first = Product.objects.first()
        if not first:
            return redirect("index")
        return redirect("product_detail", slug=first.slug)
    product = get_object_or_404(Product, slug=slug)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    return render(request, "shop/product_detail.html", {"product": product, "related_products": related_products})


@require_POST
def cart_add(request, product_id):
    _seed_demo_data()
    product = get_object_or_404(Product, id=product_id)
    qty = int(request.POST.get("quantity", 1))
    add_to_cart(request.session, product.id, qty)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "cart"
    return redirect(next_url)


@require_POST
def cart_update(request, product_id):
    qty = int(request.POST.get("quantity", 1))
    set_quantity(request.session, product_id, qty)
    return redirect("cart")


@require_POST
def cart_remove(request, product_id):
    remove_from_cart(request.session, product_id)
    return redirect("cart")


@require_POST
def quick_order(request, product_id):
    _seed_demo_data()
    product = get_object_or_404(Product, id=product_id)
    try:
        qty = max(1, int(request.POST.get("quantity", 1) or 1))
    except (TypeError, ValueError):
        qty = 1
    customer_name = request.POST.get("customer_name", "").strip()
    phone = request.POST.get("phone", "").strip()
    comment = request.POST.get("comment", "").strip()
    if not customer_name or not phone:
        return redirect("product_detail", slug=product.slug)
    order = Order.objects.create(
        customer_name=customer_name,
        phone=phone,
        address="(уточнить по телефону)",
        comment=comment,
        total_price=product.price * qty,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=qty,
        unit_price=product.price,
    )
    return redirect("checkout_success", order_id=order.id)


def cart_page(request):
    items, total = build_cart_items(request.session)
    return render(request, "shop/cart.html", {"cart_items": items, "cart_total": total})


def checkout(request):
    items, total = build_cart_items(request.session)
    if not items:
        return redirect("cart")

    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()
        comment = request.POST.get("comment", "").strip()

        if customer_name and phone and address:
            order = Order.objects.create(
                customer_name=customer_name,
                phone=phone,
                email=email,
                address=address,
                comment=comment,
                total_price=total,
            )
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=item["product"],
                        quantity=item["quantity"],
                        unit_price=item["product"].price,
                    )
                    for item in items
                ]
            )
            clear_cart(request.session)
            return redirect("checkout_success", order_id=order.id)

        return render(
            request,
            "shop/checkout.html",
            {
                "cart_items": items,
                "cart_total": total,
                "error": "Заполните обязательные поля: имя, телефон и адрес.",
            },
        )

    return render(request, "shop/checkout.html", {"cart_items": items, "cart_total": total})


def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "shop/checkout_success.html", {"order": order})


def search(request):
    query = request.GET.get("q", "").strip()
    products = Product.objects.none()
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query)
        )
    return render(request, "shop/search.html", {"query": query, "products": products})


def _orders_for_user(request):
    if request.user.is_authenticated and request.user.email:
        return Order.objects.filter(email__iexact=request.user.email).prefetch_related("items", "items__product")[:20]
    return Order.objects.prefetch_related("items", "items__product")[:20]


def _redirect_after_favorite(request):
    next_url = (request.POST.get("next") or "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(reverse("index"))


@login_required(login_url=reverse_lazy("index"))
@require_POST
def favorite_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    fav = Favorite.objects.filter(user=request.user, product_id=product.id).first()
    if fav:
        fav.delete()
    else:
        Favorite.objects.get_or_create(user=request.user, product=product)
    return _redirect_after_favorite(request)


@login_required(login_url=reverse_lazy("index"))
def account_favorites(request):
    favorites = Favorite.objects.filter(user=request.user).select_related("product").order_by("-created_at")
    return render(request, "shop/account_favorites.html", {"favorites": favorites})


@login_required
def account(request):
    return render(request, "shop/account.html")


@login_required
def account_orders(request):
    orders = _orders_for_user(request)
    return render(request, "shop/account_orders.html", {"orders": orders})


def _personal_notice_message(request):
    key = (request.GET.get("notice") or "").strip()
    return {
        "profile_saved": "Личные данные сохранены.",
        "password_changed": "Пароль успешно изменён.",
    }.get(key, "")


@login_required
def account_personal_data(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(
        request,
        "shop/account_personal_data.html",
        {
            "profile": profile,
            "personal_success": _personal_notice_message(request),
        },
    )


@login_required
def account_personal_data_edit(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        user.first_name = first_name[:150]
        user.last_name = last_name[:150]
        user.save(update_fields=["first_name", "last_name"])
        profile.phone = phone[:32]
        profile.save(update_fields=["phone"])
        return redirect(f"{reverse('account_personal_data')}?notice=profile_saved")

    return render(
        request,
        "shop/account_personal_data_edit.html",
        {"profile": profile},
    )


@login_required
def account_password_change(request):
    user = request.user
    password_error = ""

    if request.method == "POST":
        old_password = request.POST.get("old_password") or ""
        new_password1 = request.POST.get("new_password1") or ""
        new_password2 = request.POST.get("new_password2") or ""
        if not user.check_password(old_password):
            password_error = "Неверный текущий пароль."
        elif len(new_password1) < 6:
            password_error = "Новый пароль должен быть не короче 6 символов."
        elif new_password1 != new_password2:
            password_error = "Новые пароли не совпадают."
        else:
            user.set_password(new_password1)
            user.save(update_fields=["password"])
            update_session_auth_hash(request, user)
            return redirect(f"{reverse('account_personal_data')}?notice=password_changed")

    return render(
        request,
        "shop/account_password_change.html",
        {"password_error": password_error},
    )


def _organization_form_from_post(post):
    return {
        "name": (post.get("name") or "").strip(),
        "inn": (post.get("inn") or "").strip(),
        "kpp": (post.get("kpp") or "").strip(),
        "legal_address": (post.get("legal_address") or "").strip(),
    }


def _validate_organization(owner, form_data, *, exclude_org=None):
    if not form_data["name"] or not form_data["inn"]:
        return "Заполните обязательные поля: название и ИНН."
    if not form_data["inn"].isdigit() or len(form_data["inn"]) not in (10, 12):
        return "ИНН должен содержать 10 или 12 цифр."
    if form_data["kpp"] and (not form_data["kpp"].isdigit() or len(form_data["kpp"]) != 9):
        return "КПП должен содержать 9 цифр."
    qs = Organization.objects.filter(owner=owner, inn=form_data["inn"])
    if exclude_org is not None:
        qs = qs.exclude(pk=exclude_org.pk)
    if qs.exists():
        return "Организация с таким ИНН уже добавлена."
    return None


def _notice_message(request):
    key = (request.GET.get("notice") or "").strip()
    messages_map = {
        "created": "Организация успешно добавлена.",
        "updated": "Изменения сохранены.",
        "deleted": "Организация удалена.",
    }
    return messages_map.get(key, "")


@login_required
def account_organizations(request):
    organizations = Organization.objects.filter(owner=request.user)
    notice_success = _notice_message(request)

    editing_org = None
    edit_pk = request.GET.get("edit")
    if edit_pk:
        try:
            editing_org = organizations.filter(pk=int(edit_pk)).first()
        except (TypeError, ValueError):
            editing_org = None

    empty_form = {"name": "", "inn": "", "kpp": "", "legal_address": ""}

    if editing_org:
        org_form = {
            "name": editing_org.name,
            "inn": editing_org.inn,
            "kpp": editing_org.kpp or "",
            "legal_address": editing_org.legal_address or "",
        }
    else:
        org_form = dict(empty_form)

    error = ""
    success = notice_success

    if request.method == "POST":
        action = (request.POST.get("action") or "create").strip()
        form_data = _organization_form_from_post(request.POST)

        if action == "delete":
            raw_id = request.POST.get("org_id")
            try:
                org = organizations.get(pk=int(raw_id))
            except (TypeError, ValueError, Organization.DoesNotExist):
                error = "Не удалось удалить организацию."
            else:
                org.delete()
                return redirect(f"{reverse('account_organizations')}?notice=deleted")

        elif action == "update":
            raw_id = request.POST.get("org_id")
            try:
                org = organizations.get(pk=int(raw_id))
            except (TypeError, ValueError, Organization.DoesNotExist):
                error = "Организация не найдена."
                org_form = form_data
                editing_org = None
            else:
                editing_org = org
                org_form = form_data
                err = _validate_organization(request.user, form_data, exclude_org=org)
                if err:
                    error = err
                else:
                    org.name = form_data["name"]
                    org.inn = form_data["inn"]
                    org.kpp = form_data["kpp"]
                    org.legal_address = form_data["legal_address"]
                    org.save()
                    return redirect(f"{reverse('account_organizations')}?notice=updated")

        else:
            org_form = form_data
            editing_org = None
            err = _validate_organization(request.user, form_data)
            if err:
                error = err
            else:
                Organization.objects.create(owner=request.user, **form_data)
                return redirect(f"{reverse('account_organizations')}?notice=created")

    show_edit_form = editing_org is not None
    show_create_form = editing_org is None and (
        request.GET.get("create") == "1"
        or (
            request.method == "POST"
            and (request.POST.get("action") or "create").strip() == "create"
            and error
        )
    )

    organizations = Organization.objects.filter(owner=request.user)

    return render(
        request,
        "shop/account_organizations.html",
        {
            "organizations": organizations,
            "org_form": org_form,
            "org_error": error,
            "org_success": success,
            "show_create_form": show_create_form,
            "show_edit_form": show_edit_form,
            "editing_org": editing_org,
        },
    )


@require_POST
def auth_email_check(request):
    email = (request.POST.get("email") or "").strip().lower()
    if not email:
        return JsonResponse({"ok": False, "error": "Введите email."}, status=400)
    exists = User.objects.filter(email__iexact=email).exists()
    return JsonResponse({"ok": True, "exists": exists, "email": email})


@require_POST
def auth_login(request):
    email = (request.POST.get("email") or "").strip().lower()
    password = request.POST.get("password") or ""
    if not email or not password:
        return JsonResponse({"ok": False, "error": "Введите email и пароль."}, status=400)
    user = authenticate(request, username=email, password=password)
    if not user:
        return JsonResponse({"ok": False, "error": "Неверный email или пароль."}, status=400)
    if not user.is_active:
        return JsonResponse({"ok": False, "error": "Подтвердите email, затем выполните вход."}, status=400)
    login(request, user)
    return JsonResponse({"ok": True, "redirect_url": request.POST.get("next") or "/"})


@require_POST
def auth_register(request):
    email = (request.POST.get("email") or "").strip().lower()
    password1 = request.POST.get("password1") or ""
    password2 = request.POST.get("password2") or ""

    if not email:
        return JsonResponse({"ok": False, "error": "Введите email."}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"ok": False, "error": "Пользователь с таким email уже существует."}, status=400)
    if len(password1) < 6:
        return JsonResponse({"ok": False, "error": "Пароль должен быть не короче 6 символов."}, status=400)
    if password1 != password2:
        return JsonResponse({"ok": False, "error": "Пароли не совпадают."}, status=400)

    user = User.objects.create_user(username=email, email=email, password=password1, is_active=False)
    try:
        _send_confirmation_email(request, user)
    except Exception:
        user.delete()
        return JsonResponse(
            {"ok": False, "error": "Не удалось отправить письмо подтверждения. Попробуйте позже."},
            status=500,
        )
    return JsonResponse({"ok": True, "email": email})


@require_POST
def auth_logout(request):
    logout(request)
    return redirect(request.POST.get("next") or "index")


def auth_confirm_email(request, token):
    user = _parse_email_confirmation_token(token)
    if not user:
        return render(
            request,
            "shop/auth_confirm_email_result.html",
            {"success": False, "title": "Ссылка недействительна", "message": "Проверьте ссылку или запросите регистрацию заново."},
        )
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    login(request, user)
    return render(
        request,
        "shop/auth_confirm_email_result.html",
        {"success": True, "title": "Email подтвержден", "message": "Аккаунт активирован, вы успешно вошли в систему."},
    )
