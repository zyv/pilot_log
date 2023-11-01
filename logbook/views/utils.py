from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView


class AuthenticatedView(UserPassesTestMixin, LoginRequiredMixin):
    login_url = reverse_lazy("admin:login")

    def test_func(self):
        return self.request.user.is_staff


class AuthenticatedTemplateView(AuthenticatedView, TemplateView):
    pass


class AuthenticatedListView(AuthenticatedView, ListView):
    pass
