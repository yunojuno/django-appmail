# Generated by Django 3.1.5 on 2021-01-04 06:48

import django.core.serializers.json
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("appmail", "0006_emailtemplate_supports_attachments"),
    ]

    operations = [
        migrations.CreateModel(
            name="LoggedMessage",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "to",
                    models.EmailField(
                        help_text="Address to which the the Email was sent.",
                        max_length=254,
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="When the email was sent.",
                        db_index=True,
                    ),
                ),
                (
                    "subject",
                    models.TextField(blank=True, help_text="Email subject line."),
                ),
                (
                    "body",
                    models.TextField(
                        blank=True,
                        help_text="Plain text content.",
                        verbose_name="Plain text",
                    ),
                ),
                (
                    "html",
                    models.TextField(
                        blank=True, help_text="HTML content.", verbose_name="HTML"
                    ),
                ),
                (
                    "context",
                    models.JSONField(
                        default=dict,
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        help_text="Appmail template context.",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        blank=True,
                        help_text="The appmail template used.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="logged_emails",
                        to="appmail.emailtemplate",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="logged_emails",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "get_latest_by": "timestamp",
                "verbose_name": "Email message",
                "verbose_name_plural": "Email messages sent",
            },
        ),
    ]
