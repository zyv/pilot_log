from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.generic import ListView, TemplateView

from ..models import Certificate

EXPIRY_WARNING_THRESHOLD = relativedelta(months=3)


def check_certificates_expiry(request):
    today = datetime.now(tz=UTC).date()
    for certificate in Certificate.objects.filter(
        valid_until__lte=today + EXPIRY_WARNING_THRESHOLD,
        supersedes_set=None,
    ):
        designation = f'Certificate <strong>"{escape(certificate.name)}"</strong> issued on {certificate.issue_date}'
        if not certificate.valid:
            messages.error(
                request,
                mark_safe(f"{designation} has expired on {certificate.valid_until}!"),
            )
        else:
            messages.warning(
                request,
                mark_safe(f"{designation} expires in <strong>{(certificate.valid_until - today).days}</strong> days!"),
            )


class AuthenticatedView(UserPassesTestMixin, LoginRequiredMixin):
    login_url = reverse_lazy("admin:login")

    def test_func(self):
        return self.request.user.is_staff


class AuthenticatedTemplateView(AuthenticatedView, TemplateView):
    pass


class AuthenticatedListView(AuthenticatedView, ListView):
    pass
