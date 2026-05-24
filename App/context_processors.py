from .access_control import build_accessible_menu, get_user_permission_codenames


def access_control(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return {
        "accessible_menu": build_accessible_menu(user),
        "user_permissions": get_user_permission_codenames(user),
    }
