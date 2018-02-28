try:
    from django.urls import re_path
except ImportError:
    from django.conf.urls import url as re_path

from .views import (
    render_template_body,
    render_template_subject,
    send_test_email
)

app_name = 'appmail'

urlpatterns = [
    re_path(
        r'^templates/(?P<template_id>\d+)/body.txt$',
        render_template_body,
        kwargs={'content_type': 'text/plain'},
        name="render_template_body_text"
    ),
    re_path(
        r'^templates/(?P<template_id>\d+)/body.html$',
        render_template_body,
        kwargs={'content_type': 'text/html'},
        name="render_template_body_html"
    ),
    re_path(
        r'^templates/(?P<template_id>\d+)/subject.txt$',
        render_template_subject,
        name="render_template_subject"
    ),
    re_path(
        r'^templates/test/$',
        send_test_email,
        name="send_test_email"
    ),
]
