from .cart import cart_count
from .models import Favorite


def cart_context(request):
    return {"cart_items_count": cart_count(request.session)}


def favorites_context(request):
    if request.user.is_authenticated:
        ids = frozenset(Favorite.objects.filter(user=request.user).values_list("product_id", flat=True))
        return {"favorite_product_ids": ids, "favorites_count": len(ids)}
    return {"favorite_product_ids": frozenset(), "favorites_count": 0}
