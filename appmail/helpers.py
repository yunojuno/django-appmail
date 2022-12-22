from __future__ import annotations

import re
from typing import Callable, Iterable

from django.http import HttpRequest

# regex for extracting django template {{ variable }}s
TEMPLATE_VARS = re.compile(r"{{([ ._[a-z]*)}}")


def get_context(content: str) -> dict:
    """
    Return a dummary context dict for a content block.

    This function works by taking template content,
    extracting the template variables ({{ foo.bar }}),
    expanding out the list of variables into a dict
    using the '.' separator, and then populating the
    value of each leaf node with the node key ('foo': "FOO").

    Used for generating test data.

    """
    return fill_leaf_values(expand_list(extract_vars(content)))


def extract_vars(content: str) -> list[str]:
    """
    Extract variables from template content.

    Returns a deduplicated list of all the variable names
    found in the content.

    """
    content = content or ""
    # if I was better at regex I wouldn't need the strip.
    return list({s.strip() for s in TEMPLATE_VARS.findall(content)})


def expand_list(_list: list[str]) -> dict:
    """
    Convert list of '.' separated values to a nested dict.

    Taken from SO article which I now can't find, this will take a list
    and return a dictionary which contains an empty dict as each leaf
    node.

        >>> expand_list(['a', 'b.c'])
        {
            'a': {},
            'b': {
                'c': {}
            }
        }

    """
    if not isinstance(_list, list):
        raise ValueError("arg must be a list")
    tree = {}  # type: dict[str, dict]
    for item in _list:
        t = tree
        for part in item.split("."):
            t = t.setdefault(part, {})
    return tree


def fill_leaf_values(tree: dict) -> dict:
    """
    Recursive function that populates empty dict leaf nodes.

    This function will look for all the leaf nodes in a dictionary
    and replace them with a value that looks like the variable
    in the template - e.g. {{ foo }}.

        >>> fill_leaf_values({'a': {}, 'b': 'c': {}})
        {
            'a': '{{ A }}',
            'b': {
                'c': '{{ C }}'
            }
        }

    """
    if not isinstance(tree, dict):
        raise ValueError("arg must be a dictionary")
    for k in tree.keys():
        if tree[k] == {}:
            tree[k] = k.upper()
        else:
            fill_leaf_values(tree[k])
    return tree


def merge_dicts(*dicts: dict) -> dict:
    """Merge multiple dicts into one."""
    context = {}
    for d in dicts:
        context.update(d)
    return context


def patch_context(
    context: dict,
    processors: Iterable[Callable[[HttpRequest], dict]],
    request: HttpRequest | None = None,
) -> dict:
    """Add template context_processor content to context."""
    cpx = [p(request) for p in processors]
    return merge_dicts(context, *cpx)
