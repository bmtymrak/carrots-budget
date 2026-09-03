from allauth.account.views import LoginView
from django.shortcuts import redirect


class HomePageView(LoginView):
    """Present the landing page without bypassing allauth's login safeguards."""

    template_name = "home.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("yearly_list")
        return super().dispatch(request, *args, **kwargs)
