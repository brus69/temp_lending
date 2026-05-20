from django_ckeditor_5.widgets import CKEditor5Widget


class RichTextAdminMixin:
    """Подключает CKEditor 5 к текстовым полям ModelAdmin."""

    rich_text_field = "body"
    rich_text_fields: tuple[str, ...] | None = None
    ckeditor_config_name = "default"

    def get_rich_text_fields(self) -> tuple[str, ...]:
        if self.rich_text_fields is not None:
            return self.rich_text_fields
        return (self.rich_text_field,)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name in self.get_rich_text_fields():
            if field_name in form.base_fields:
                form.base_fields[field_name].widget = CKEditor5Widget(
                    config_name=self.ckeditor_config_name,
                )
        return form
