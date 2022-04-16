from django.shortcuts import render, redirect
from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = "home.html"

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(
                self, request.method.lower(), self.http_method_not_allowed
            )
        else:
            handler = self.http_method_not_allowed

        if self.request.user:
            return redirect("yearly_list")
        else:
            return handler(request, *args, **kwargs)
