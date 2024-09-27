from os.path import splitext

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .storage import ResumableStorage


class StorageFileValidator(object):
    """
    Validation of uploaded files.

    Files uploaded using the library are passed to application with their names only.
    Any validation must happen either on the client-side or requires upload to be completed
    and file saved in application storage.
    """
    messages = {
        'file': _(u"File {name} does not exist."),
        'extension': _(u"Extension {extension} not allowed. Allowed extensions are: {allowed_extensions}"),
        'min_size': _(u"File {name} too small ({size} bytes). The minimum file size is {min_size} bytes."),
        'max_size': _(u"File {name} too large ({size} bytes). The maximum file size is {max_size} bytes."),
    }

    def __init__(self, min_size=0, max_size=None, allowed_extensions=None):
        self.min_size = min_size
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions or []

    def get_storage(self):
        return ResumableStorage().get_persistent_storage()

    def validate_extension(self, value):
        ext = splitext(value)[1].lower()
        if self.allowed_extensions and ext not in self.allowed_extensions:
            message = self.messages['extension'].format(**{
                'extension': ext,
                'allowed_extensions': ', '.join(self.allowed_extensions)
            })
            raise ValidationError(message)

    def validate_exists(self, value, storage):
        if not storage.exists(value):
            message = self.messages['file'].format(**{
                'name': value,
            })
            raise ValidationError(message)

    def validate_size(self, value, storage):
        size = storage.size(value)
        if size > self.max_size:
            message = self.messages['max_size'].format(**{
                'name': value,
                'size': size,
                'max_size': self.max_size,
            })
            raise ValidationError(message)
        elif size < self.min_size:
            message = self.messages['min_size'].format(**{
                'name': value,
                'size': size,
                'min_size': self.min_size,
            })
            raise ValidationError(message)

    def __call__(self, value):
        assert type(value) is str
        storage = self.get_storage()
        self.validate_exists(value, storage)
        self.validate_extension(value)
        self.validate_size(value, storage)
