# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-05-06 08:15
from __future__ import unicode_literals

from django.db import migrations

from ..compat import JSONField


class Migration(migrations.Migration):

    dependencies = [("appmail", "0002_add_template_description")]

    operations = [
        migrations.AddField(
            model_name="emailtemplate",
            name="test_context",
            field=JSONField(
                default=dict,
                blank=True,
                help_text=(
                    "Dummy JSON used for test rendering (set automatically on first "
                    "save)."
                ),
            ),
        )
    ]
