"""
Competency mapping: working out who is actually qualified to teach a subject,
and which subjects nobody is qualified to teach.

The score is a weighted average of three things SkillScope already collects.
There is no hidden model and nothing is trained -- which is deliberate. Every
number that goes into a ranking can be pointed at on screen and explained.

    40%  how skilled they say they are, rated 1-5 on their profile
    30%  how many years they have worked in that subject, capped at 10
    30%  how learners have rated their teaching, out of 5

    60 or above counts as qualified to teach the subject.
"""

from decimal import Decimal

from django.db.models import Avg

from accounts.models import Role, User
from learning.models import Experience, Feedback, Subject, UserSkill

WEIGHT_SKILL = 40
WEIGHT_EXPERIENCE = 30
WEIGHT_RATING = 30

# Ten years of work in a subject counts as full marks. Without a cap, one very
# long career would swamp the other two factors entirely.
EXPERIENCE_CAP_YEARS = 10

# A trainer nobody has rated yet is treated as average rather than as zero.
# Scoring them zero would mean a new trainer could never be recommended, and
# so could never earn the ratings that would fix it.
NEUTRAL_RATING = Decimal("3.0")

QUALIFIED_THRESHOLD = 60


def score_trainer_for_subject(trainer, subject) -> dict:
    """
    Score one trainer against one subject, out of 100.

    Returns the parts as well as the total, because the parts are what the
    screen shows -- a bare number nobody can question is worth less than a
    number with its reasoning attached.
    """
    # --- 1. skill, from the profile -------------------------------------
    avg_proficiency = UserSkill.objects.filter(
        user=trainer, subject=subject
    ).aggregate(v=Avg("proficiency"))["v"]
    skill_ratio = Decimal(str(avg_proficiency or 0)) / 5
    skill_points = skill_ratio * WEIGHT_SKILL

    # --- 2. experience, from the work history ---------------------------
    total_years = sum(
        e.years for e in Experience.objects.filter(user=trainer, subject=subject)
    )
    capped_years = min(total_years, EXPERIENCE_CAP_YEARS)
    experience_ratio = Decimal(capped_years) / EXPERIENCE_CAP_YEARS
    experience_points = experience_ratio * WEIGHT_EXPERIENCE

    # --- 3. teaching rating, from learner feedback ----------------------
    avg_rating = Feedback.objects.filter(
        course__trainer=trainer, course__subject=subject
    ).aggregate(v=Avg("trainer_rating"))["v"]
    rating_count = Feedback.objects.filter(
        course__trainer=trainer, course__subject=subject
    ).count()
    rating_value = Decimal(str(avg_rating)) if avg_rating else NEUTRAL_RATING
    rating_ratio = rating_value / 5
    rating_points = rating_ratio * WEIGHT_RATING

    total = skill_points + experience_points + rating_points

    return {
        "trainer": trainer,
        "subject": subject,
        "total": int(round(total)),
        "qualified": total >= QUALIFIED_THRESHOLD,
        "skill": {
            "points": round(float(skill_points), 1),
            "max": WEIGHT_SKILL,
            "percent": round(float(skill_ratio * 100)),
            "detail": f"{float(avg_proficiency):.1f} of 5" if avg_proficiency else "no skills listed",
        },
        "experience": {
            "points": round(float(experience_points), 1),
            "max": WEIGHT_EXPERIENCE,
            "percent": round(float(experience_ratio * 100)),
            "detail": f"{total_years} year{'s' if total_years != 1 else ''}",
        },
        "rating": {
            "points": round(float(rating_points), 1),
            "max": WEIGHT_RATING,
            "percent": round(float(rating_ratio * 100)),
            "detail": (
                f"{float(rating_value):.1f} of 5 from {rating_count} learner"
                f"{'s' if rating_count != 1 else ''}"
                if rating_count else "not yet rated"
            ),
        },
    }


def rank_trainers_for_subject(subject, institution=None):
    """Every trainer scored against one subject, best first."""
    trainers = User.objects.filter(role=Role.TRAINER, is_active=True)
    if institution is not None:
        trainers = trainers.filter(institution=institution)

    scores = [score_trainer_for_subject(t, subject) for t in trainers.select_related("institution")]
    scores.sort(key=lambda s: s["total"], reverse=True)
    return scores


def competency_gaps(institution=None):
    """
    The other direction: for each subject, how many people could actually
    teach it.

    This is the question a training department really has -- not "who is our
    best trainer" but "what can we not teach at all". A subject with nobody
    above the threshold is a gap that has to be hired or trained into.
    """
    trainers = User.objects.filter(role=Role.TRAINER, is_active=True)
    if institution is not None:
        trainers = trainers.filter(institution=institution)
    trainers = list(trainers)

    rows = []
    for subject in Subject.objects.all():
        scored = [score_trainer_for_subject(t, subject) for t in trainers]
        qualified = [s for s in scored if s["qualified"]]
        best = max(scored, key=lambda s: s["total"]) if scored else None

        if len(qualified) == 0:
            level = "red"
            note = "No qualified trainer"
        elif len(qualified) <= 2:
            level = "amber"
            note = f"{len(qualified)} qualified trainer{'s' if len(qualified) != 1 else ''}"
        else:
            level = "green"
            note = f"{len(qualified)} qualified trainers"

        rows.append({
            "subject": subject,
            "qualified_count": len(qualified),
            "level": level,
            "note": note,
            "best": best,
        })

    # Weakest subjects first: that is the list somebody has to act on.
    rows.sort(key=lambda r: (r["qualified_count"], -(r["best"]["total"] if r["best"] else 0)))
    return rows


def trainer_profile_scores(trainer):
    """One trainer scored across every subject, for their competency chart."""
    scores = [score_trainer_for_subject(trainer, s) for s in Subject.objects.all()]
    scores.sort(key=lambda s: s["total"], reverse=True)
    return scores
