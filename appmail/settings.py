# -*- coding: utf-8 -*-
from django.conf import settings

# Validate that EmailTemplate can be rendered without
# error on each save. Defaults to True.
VALIDATE_ON_SAVE = getattr(settings, 'APPMAIL_VALIDATE_ON_SAVE', True)
