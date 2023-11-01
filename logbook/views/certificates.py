from ..models import Certificate
from .utils import AuthenticatedListView, check_certificates_expiry


class CertificateIndexView(AuthenticatedListView):
    model = Certificate

    def get(self, request, *args, **kwargs):
        check_certificates_expiry(request)
        return super().get(request, *args, **kwargs)
