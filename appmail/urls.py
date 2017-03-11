# -*- coding: utf-8 -*-
"""onfido urls."""
from django.conf.urls import url

from .views import (
    render_template_body,
    render_template_subject
)

urlpatterns = [
    url(
        r'^templates/(?P<template_id>\d+)/body$',
        render_template_body,
        name="render_template_body"
    ),
    url(
        r'^templates/(?P<template_id>\d+)/subject$',
        render_template_subject,
        name="render_template_subject"
    ),
]
