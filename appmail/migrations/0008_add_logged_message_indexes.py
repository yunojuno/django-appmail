# Generated by Django 4.1.4 on 2022-12-21 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appmail", "0007_loggedemailmessage"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="loggedmessage",
            index=models.Index(fields=["to"], name="appmail_log_to_e76fc8_idx"),
        ),
        migrations.AddIndex(
            model_name="loggedmessage",
            index=models.Index(
                fields=["subject"], name="appmail_log_subject_d9fc7b_idx"
            ),
        ),
    ]
