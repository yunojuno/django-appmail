# Changelog

All notable changes to this project will be documented in this file.

## v6.0.0

* Add support for Django 5.0
* Add Python 3.12 to classifiers and build matrix

## v5.0.0

* Improve LoggedMessage admin list page performance.
* Add support for Django 4.2
* Drop support for Python 3.8

## v4.0.0

Bump in version due to potential breaking change.

* [Potential breaking change] New indexes on the LoggedMessage model; take
care when applying this migration as your table may be large in size.
* Fix crash in admin logged messages when a related template has been deleted.
* Fix n+1 query issue in logged messages admin listing.

## v3.0.0

* Add support for Python 3.11.
* Drop support for Django 3.0, 3.1.

## v2.3.0

* Add Django 4.1 to build matrix.

## v2.2.0

* Add management command to truncate logs after a period.

## v2.1.0

* Add Python 3.10 to build matrix.
* Add Django 4.0 to build matrix.
* Update admin template to fix subject line render issue.
* Update `EmailTemplate.clone` to make new template inactive by default.

## v2.0.0

* Drop support for Django 2.x.
* Add abililty to send / log messages from templates.
