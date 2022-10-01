from ..models import Certificate
from .utils import AuthenticatedListView


class CertificateIndexView(AuthenticatedListView):
    model = Certificate
