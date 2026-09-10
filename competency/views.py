"""
The competency screens.

Both admin levels see the same two views of the same scoring engine, over a
different slice of trainers:

    institute admin -> only their own institution's trainers
    platform admin  -> every trainer on the platform
"""

from django.shortcuts import get_object_or_404, render

from accounts.permissions import institute_admin_required, platform_admin_required
from competency.services import (
    QUALIFIED_THRESHOLD, WEIGHT_EXPERIENCE, WEIGHT_RATING, WEIGHT_SKILL,
    competency_gaps, rank_trainers_for_subject,
)
from learning.models import Subject

WEIGHTS = {
    "skill": WEIGHT_SKILL,
    "experience": WEIGHT_EXPERIENCE,
    "rating": WEIGHT_RATING,
    "threshold": QUALIFIED_THRESHOLD,
}


def _competency_page(request, institution, template):
    """
    Shared by both admin levels. `institution` is None for a platform admin,
    which is what widens the scoring to every trainer.
    """
    subjects = Subject.objects.all()
    selected_id = request.GET.get("subject")

    selected = None
    ranked = []
    if selected_id:
        selected = get_object_or_404(Subject, pk=selected_id)
        ranked = rank_trainers_for_subject(selected, institution=institution)

    return render(request, template, {
        "subjects": subjects,
        "selected": selected,
        "ranked": ranked,
        "gaps": competency_gaps(institution=institution),
        "weights": WEIGHTS,
        "institution": institution,
    })


@institute_admin_required
def institute_competency(request):
    return _competency_page(request, request.user.institution, "institute/competency.html")


@platform_admin_required
def platform_competency(request):
    return _competency_page(request, None, "platform/competency.html")


@platform_admin_required
def subject_trainers(request, subject_id):
    """Every trainer on the platform, ranked for one subject."""
    subject = get_object_or_404(Subject, pk=subject_id)
    return render(request, "platform/subject_trainers.html", {
        "subject": subject,
        "ranked": rank_trainers_for_subject(subject),
        "weights": WEIGHTS,
    })
