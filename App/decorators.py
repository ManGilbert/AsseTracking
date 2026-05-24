from functools import wraps
from django.shortcuts import redirect
from .access_control import user_has_permission


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated or request.user.role not in roles:
                return redirect("login")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def permission_required(codename):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated or not user_has_permission(request.user, codename):
                return redirect("login")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
