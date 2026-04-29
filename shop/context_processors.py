from .cart import cart_count


def cart_context(request):
    return {"cart_items_count": cart_count(request.session)}
