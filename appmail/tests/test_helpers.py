# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from .. import helpers


class HelperTests(TestCase):

    """appmail.helpers module tests."""

    def test_get_context(self):
        self.assertEqual(
            helpers.get_context('{{a}} {{b.c}}'),
            {
                'a': "A",
                'b': {
                    'c': "C"
                }
            }
        )

    def test_extract_vars(self):
        """Check extract_vars handles expected input."""
        for x, y in (
            ('', []),
            (None, []),
            ('{{foo}}', ['foo']),
            ('{{ foo}}', ['foo']),
            ('{{ foo }}', ['foo']),
            ('{{ foo }', []),
            ('{% foo %}', []),
            ('{{ foo|time }}', []),
            ('{{foo}} {{bar}}', ['foo', 'bar']),
        ):
            self.assertEqual(set(helpers.extract_vars(x)), set(y))

    def test_expand_list(self):
        """Check dot notation expansion."""
        self.assertRaises(AssertionError, helpers.expand_list, None)
        self.assertRaises(AssertionError, helpers.expand_list, '')
        self.assertEqual(
            helpers.expand_list(['a', 'b.c']),
            {
                'a': {},
                'b': {
                    'c': {}
                }
            }
        )

    def test_fill_leaf_values(self):
        """Check the default func is applied."""
        self.assertRaises(AssertionError, helpers.fill_leaf_values, None)
        self.assertRaises(AssertionError, helpers.fill_leaf_values, '')
        self.assertEqual(
            helpers.fill_leaf_values(
                {
                    'a': {},
                    'b': {
                        'c': {}
                    }
                }
            ),
            {
                'a': "A",
                'b': {
                    'c': "C"
                }
            }
        )

    def test_merge_dicts(self):
        self.assertEqual(
            helpers.merge_dicts({'foo': 1}),
            {'foo': 1}
        )
        self.assertEqual(
            helpers.merge_dicts({'foo': 1}, {'bar': 2}),
            {'foo': 1, 'bar': 2}
        )
        self.assertEqual(
            helpers.merge_dicts({'foo': 1}, {'foo': 2}),
            {'foo': 2}
        )

    def test_patch_context(self):

        foo = {'foo': 1}
        bar = {'bar': 2}
        baz = {'baz': 3}

        def cp1(request):
            return bar

        def cp2(request):
            return baz

        self.assertEqual(
            helpers.patch_context(foo, []),
            foo
        )

        self.assertEqual(
            helpers.patch_context(foo, [cp1]),
            helpers.merge_dicts(foo, bar)
        )

        self.assertEqual(
            helpers.patch_context(foo, [cp1, cp2]),
            helpers.merge_dicts(foo, bar, baz)
        )
