from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone


class InactiveUserAndSessionTimeoutMiddleware:
    """Block inactive users and expire web sessions after inactivity."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            if not user.is_active:
                logout(request)
                messages.error(
                    request,
                    "Your account is inactive. Please contact the administrator.",
                )
                return redirect(settings.LOGIN_URL)

            now = timezone.now()
            last_activity = request.session.get("last_activity_at")
            timeout_seconds = getattr(settings, "SESSION_INACTIVITY_TIMEOUT", 3600)

            if last_activity:
                last_activity_dt = timezone.datetime.fromisoformat(last_activity)
                if timezone.is_naive(last_activity_dt):
                    last_activity_dt = timezone.make_aware(last_activity_dt)
                if (now - last_activity_dt).total_seconds() > timeout_seconds:
                    logout(request)
                    messages.error(
                        request,
                        "Your session has expired due to inactivity. Please log in again.",
                    )
                    return redirect(settings.LOGIN_URL)

            request.session["last_activity_at"] = now.isoformat()

        return self.get_response(request)
