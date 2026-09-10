"""
Small template helpers.

Django templates cannot look a dictionary up by a variable key -- writing
{{ attempts.a.id }} looks for a key literally called "a.id". These fill that
gap without pushing display logic back into the views.
"""

from django import template

register = template.Library()


@register.filter
def lookup(mapping, key):
    """{{ attempts|lookup:assessment.id }} -- fetch by a variable key."""
    if hasattr(mapping, "get"):
        return mapping.get(key)
    return None


@register.filter
def percent_of(value, total):
    """Turn a count into a percentage, without dividing by zero."""
    try:
        total = float(total)
        if total == 0:
            return 0
        return round(float(value) * 100 / total)
    except (TypeError, ValueError):
        return 0


@register.filter
def subject_colour(subject):
    """
    A stable colour class for a subject, e.g. "ss-sub-3".

    Derived from the subject's id so the same subject keeps the same colour on
    every page and after a restart -- the catalogue can then be scanned by
    colour instead of read word by word.
    """
    if subject is None:
        return "ss-sub-1"
    key = getattr(subject, "id", subject) or 1
    return f"ss-sub-{(int(key) - 1) % 8 + 1}"


@register.filter
def material_icon(resource_type):
    """Which icon goes with a kind of study material."""
    return {
        "VIDEO": "video",
        "PPT": "slides",
        "PDF": "pdf",
        "DOC": "doc",
        "LINK": "link",
    }.get(resource_type, "doc")
