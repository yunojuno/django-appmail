# -*- coding: utf-8 -*-
"""onfido urls."""
from django.conf.urls import url

from .views import (
    render_template_body,
    render_template_subject,
    send_test_email
)

urlpatterns = [
    url(
        r'^templates/(?P<template_id>\d+)/body.txt$',
        render_template_body,
        kwargs={'content_type': 'text/plain'},
        name="render_template_body_text"
    ),
    url(
        r'^templates/(?P<template_id>\d+)/body.html$',
        render_template_body,
        kwargs={'content_type': 'text/html'},
        name="render_template_body_html"
    ),
    url(
        r'^templates/(?P<template_id>\d+)/subject.txt$',
        render_template_subject,
        name="render_template_subject"
    ),
    url(
        r'^templates/test/$',
        send_test_email,
        name="send_test_email"
    ),
]
