# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-08-07 06:10
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("appmail", "0003_emailtemplate_test_context")]

    operations = [
        migrations.AddField(
            model_name="emailtemplate",
            name="is_active",
            field=models.BooleanField(
                default=True,
                help_text="Set to False to remove from `current` queryset.",
                verbose_name="Active (live)",
            ),
        )
    ]
