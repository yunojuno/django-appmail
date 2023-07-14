# Generated by Django 2.2.7 on 2019-11-12 07:35

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("appmail", "0005_emailtemplate_from_email__reply_to")]

    operations = [
        migrations.AddField(
            model_name="emailtemplate",
            name="supports_attachments",
            field=models.BooleanField(
                default=False,
                help_text="Does this template support file attachments?",
                verbose_name="Supports attachments",
            ),
        )
    ]
