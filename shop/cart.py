from decimal import Decimal

from .models import Product


CART_SESSION_KEY = "cart"


def get_cart(session):
    return session.get(CART_SESSION_KEY, {})


def save_cart(session, cart):
    session[CART_SESSION_KEY] = cart
    session.modified = True


def add_to_cart(session, product_id: int, quantity: int = 1):
    cart = get_cart(session)
    key = str(product_id)
    current = int(cart.get(key, 0))
    cart[key] = current + max(1, quantity)
    save_cart(session, cart)


def set_quantity(session, product_id: int, quantity: int):
    cart = get_cart(session)
    key = str(product_id)
    if quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = quantity
    save_cart(session, cart)


def remove_from_cart(session, product_id: int):
    cart = get_cart(session)
    cart.pop(str(product_id), None)
    save_cart(session, cart)


def build_cart_items(session):
    cart = get_cart(session)
    ids = [int(key) for key in cart.keys()]
    products = Product.objects.filter(id__in=ids)
    product_map = {product.id: product for product in products}

    items = []
    total = Decimal("0")
    for key, qty in cart.items():
        product = product_map.get(int(key))
        if not product:
            continue
        quantity = int(qty)
        subtotal = product.price * quantity
        total += subtotal
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal,
            }
        )
    return items, total


def cart_count(session):
    return sum(int(qty) for qty in get_cart(session).values())


def clear_cart(session):
    save_cart(session, {})
