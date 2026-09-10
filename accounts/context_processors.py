"""
Values every template can use without each view having to pass them.

Registered in settings.TEMPLATES under context_processors.
"""

from django.conf import settings


def site(request):
    return {
        "SITE_NAME": "SkillScope",
        "SITE_TAGLINE": "Learn, teach, and prove it",
        "SITE_BASE_URL": settings.SITE_BASE_URL,
        # Read by the upload script so the browser can reject an oversized
        # file before spending ten minutes sending it.
        "MAX_UPLOAD_MB": settings.MAX_UPLOAD_SIZE_MB,
    }
