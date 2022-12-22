# Changelog

All notable changes to this project will be documented in this file.

## v4.0

Bump in version due to potential breaking change.

* [Potential breaking change] New indexes on the LoggedMessage model; take
care when applying this migration as your table may be large in size.
* Fix crash in admin logged messages when a related template has been deleted.
* Fix n+1 query issue in logged messages admin listing.

## v3.0

* Add support for Python 3.11.
* Drop support for Django 3.0, 3.1.

## v2.3

* Add Django 4.1 to build matrix.

## v2.2

* Add management command to truncate logs after a period.

## v2.1

* Add Python 3.10 to build matrix.
* Add Django 4.0 to build matrix.
* Update admin template to fix subject line render issue.
* Update `EmailTemplate.clone` to make new template inactive by default.

## v2.0

* Drop support for Django 2.x.
* Add abililty to send / log messages from templates.
