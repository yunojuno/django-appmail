from __future__ import annotations

from typing import Tuple

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _lazy

from .compat import JSONField
from .forms import JSONWidget
from .models import EmailTemplate


class ValidTemplateListFilter(admin.SimpleListFilter):
    """Filter on whether the template can be rendered or not."""

    title = _lazy("Is valid")
    parameter_name = "valid"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> Tuple[Tuple[str, str], Tuple[str, str]]:
        """
        Return valid template True/False filter values tuples.

        The first element in each tuple is the coded value for the option
        that will appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.

        """
        return (("1", _lazy("True")), ("0", _lazy("False")))

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        """
        Return the filtered queryset.

        Filter based on the value provided in the query string and
        retrievable via `self.value()`.

        """
        valid_ids = []
        invalid_ids = []
        for obj in queryset:
            try:
                obj.clean()
                valid_ids.append(obj.pk)
            except ValidationError:
                invalid_ids.append(obj.pk)

        if self.value() == "1":
            return queryset.filter(pk__in=valid_ids)
        if self.value() == "0":
            return queryset.filter(pk__in=invalid_ids)


class EmailTemplateAdmin(admin.ModelAdmin):

    formfield_overrides = {JSONField: {"widget": JSONWidget}}

    list_display = (
        "name",
        "subject",
        "language",
        "version",
        "has_text",
        "has_html",
        "is_valid",
        "is_active",
    )

    list_filter = ("language", "version", ValidTemplateListFilter, "is_active")

    readonly_fields = ("render_subject", "render_text", "render_html")

    search_fields = ("name", "subject")
    actions = (
        "activate_templates",
        "deactivate_templates",
        "clone_templates",
        "send_test_emails",
    )
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "description", "language", "version", "is_active")},
        ),
        ("Email Defaults", {"fields": ("from_email", "reply_to")}),
        ("Templates", {"fields": ("subject", "body_text", "body_html")}),
        (
            "Sample Output",
            {
                "fields": (
                    "test_context",
                    "render_subject",
                    "render_text",
                    "render_html",
                )
            },
        ),
    )

    def _iframe(self, url: str) -> str:
        return format_html(
            "<iframe class='appmail' src='{}' onload='resizeIframe(this)'></iframe>"
            "<br/><a href='{}' target='_blank'>View in new tab.</a>",
            url,
            url,
        )

    # these functions are here rather than on the model so that we can get the
    # boolean icon.
    def has_text(self, obj: EmailTemplate) -> bool:
        return len(obj.body_text or "") > 0

    has_text.boolean = True  # type: ignore

    def has_html(self, obj: EmailTemplate) -> bool:
        return len(obj.body_html or "") > 0

    has_html.boolean = True  # type: ignore

    def is_valid(self, obj: EmailTemplate) -> bool:
        """Return True if the template can be rendered."""
        try:
            obj.clean()
            return True
        except ValidationError:
            return False

    is_valid.boolean = True  # type: ignore

    def render_subject(self, obj: EmailTemplate) -> str:
        if obj.id is None:
            url = ""
        else:
            url = reverse(
                "appmail:render_template_subject", kwargs={"template_id": obj.id}
            )
        return self._iframe(url)

    render_subject.short_description = "Rendered subject"  # type: ignore
    render_subject.allow_tags = True  # type: ignore

    def render_text(self, obj: EmailTemplate) -> str:
        if obj.id is None:
            url = ""
        else:
            url = reverse(
                "appmail:render_template_body_text", kwargs={"template_id": obj.id}
            )
        return self._iframe(url)

    render_text.short_description = "Rendered body (plain)"  # type: ignore
    render_text.allow_tags = True  # type: ignore

    def render_html(self, obj: EmailTemplate) -> str:
        if obj.id is None:
            url = ""
        else:
            url = reverse(
                "appmail:render_template_body_html", kwargs={"template_id": obj.id}
            )
        return self._iframe(url)

    render_html.short_description = "Rendered body (html)"  # type: ignore
    render_html.allow_tags = True  # type: ignore

    def send_test_emails(
        self, request: HttpRequest, queryset: QuerySet
    ) -> HttpResponseRedirect:
        selected = ",".join([str(s) for s in queryset.values_list("id", flat=True)])
        url = "{}?templates={}".format(reverse("appmail:send_test_email"), selected)
        return HttpResponseRedirect(url)

    send_test_emails.short_description = _lazy(  # type: ignore
        "Send test email for selected templates"
    )

    def clone_templates(
        self, request: HttpRequest, queryset: QuerySet
    ) -> HttpResponseRedirect:
        for template in queryset:
            template.clone()
            messages.success(request, _lazy("Cloned template '%s'" % template.name))
        return HttpResponseRedirect(request.path)

    clone_templates.short_description = _lazy(  # type: ignore
        "Clone selected email templates"
    )

    def activate_templates(
        self, request: HttpRequest, queryset: QuerySet
    ) -> HttpResponseRedirect:
        count = queryset.update(is_active=True)
        messages.success(request, _lazy("Activated %s templates" % count))
        return HttpResponseRedirect(request.path)

    activate_templates.short_description = _lazy(  # type: ignore
        "Activate selected email templates"
    )

    def deactivate_templates(
        self, request: HttpRequest, queryset: QuerySet
    ) -> HttpResponseRedirect:
        count = queryset.update(is_active=False)
        messages.success(request, _lazy("Deactivated %s templates" % count))
        return HttpResponseRedirect(request.path)

    deactivate_templates.short_description = _lazy(  # type: ignore
        "Deactivate selected email templates"
    )


admin.site.register(EmailTemplate, EmailTemplateAdmin)
