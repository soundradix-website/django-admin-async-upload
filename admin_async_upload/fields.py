from django.core.exceptions import ValidationError
from django.forms import fields

from .widgets import ResumableAdminWidget


def make_resumable_admin_file_fields(db_field, fieldnames, **kwargs):
    if db_field.name in fieldnames:
        defaults = {'form_class': FormResumableFileField, }
        if db_field.model:
            defaults['widget'] = ResumableAdminWidget(
                attrs={
                    'model': db_field.model,
                    'field_name': db_field.name
                }
            )
        kwargs.update(defaults)
    return kwargs


class FormResumableFileField(fields.FileField):
    widget = ResumableAdminWidget

    def to_python(self, data):
        if self.required:
            if not data or data == "None":
                raise ValidationError(self.error_messages['empty'])
        return data
