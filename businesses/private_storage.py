from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateAgreementStorage(FileSystemStorage):

    def __init__(self):
        super().__init__(
            location=settings.PRIVATE_MEDIA_ROOT
        )

    def url(self, name):
        raise NotImplementedError(
            "Private files require authenticated downloads."
        )


private_agreement_storage = PrivateAgreementStorage()