"""
The two pieces of logic that must not live in a view, because both decide
something a user would like to decide for themselves: what score they got,
and whether they have earned a certificate.

Keeping them here means there is exactly one place each rule is enforced, and
one place to point at when someone asks how marking works.
"""

import secrets
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from learning.models import (
    Assessment, Attempt, AttemptAnswer, Certificate, Enrollment, EnrollmentStatus,
)

# Ambiguous characters are left out so a code read off a printed page is not
# mistyped: no O/0, no I/1.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# ===========================================================================
# MARKING
# ===========================================================================

class DeadlinePassed(Exception):
    """Raised when someone tries to submit after the closing time."""


class AlreadyAttempted(Exception):
    """Raised when someone tries to sit an assessment they have already sat."""


@transaction.atomic
def mark_attempt(assessment: Assessment, learner, posted_answers: dict) -> Attempt:
    """
    Mark one submission and save the result.

    `posted_answers` maps a question id to the letter the learner chose, taken
    straight from the form. Note what is NOT taken from the form: the correct
    answer, the score, and whether it is a pass. Those come from the database
    and from the rules below, so editing the page in a browser changes nothing
    except which letters get marked wrong.

    The deadline is checked here rather than only in the template, because
    hiding a button does not stop anyone posting to the address directly.
    """
    if timezone.now() > assessment.deadline:
        raise DeadlinePassed(f"'{assessment.title}' closed on {assessment.deadline}.")

    if Attempt.objects.filter(assessment=assessment, learner=learner,
                              submitted_at__isnull=False).exists():
        raise AlreadyAttempted("You have already submitted this assessment.")

    questions = list(assessment.questions.all())
    total_marks = sum(q.marks for q in questions)

    attempt = Attempt.objects.create(
        assessment=assessment,
        learner=learner,
        total_marks=total_marks,
        submitted_at=timezone.now(),
    )

    score = 0
    answer_rows = []
    for question in questions:
        chosen = (posted_answers.get(str(question.id)) or "").strip().upper()
        # An unanswered question is simply wrong -- it is never skipped, or the
        # percentage would be calculated against a shrinking total.
        correct = chosen == question.correct_option
        if correct:
            score += question.marks
        answer_rows.append(AttemptAnswer(
            attempt=attempt, question=question,
            selected_option=chosen[:1], is_correct=correct,
        ))
    AttemptAnswer.objects.bulk_create(answer_rows)

    percentage = (Decimal(score) / Decimal(total_marks) * 100) if total_marks else Decimal(0)
    attempt.score = score
    attempt.percentage = percentage.quantize(Decimal("0.01"))
    # Exactly the pass mark is a pass, not a fail.
    attempt.passed = attempt.percentage >= assessment.pass_percent
    attempt.save(update_fields=["score", "percentage", "passed"])

    enrollment = Enrollment.objects.filter(
        course=assessment.course, learner=learner
    ).first()
    if enrollment:
        issue_certificate_if_earned(enrollment)

    return attempt


# ===========================================================================
# CERTIFICATES
# ===========================================================================

def _generate_verification_code() -> str:
    """A random code that cannot be guessed from the one issued before it."""
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(10))
        if not Certificate.objects.filter(verification_code=code).exists():
            return code


def _next_serial() -> str:
    """Readable and sequential, for quoting in an email or a letter."""
    year = timezone.now().year
    count = Certificate.objects.filter(serial_no__startswith=f"SS-{year}-").count()
    return f"SS-{year}-{count + 1:06d}"


def has_earned_certificate(enrollment: Enrollment) -> bool:
    """
    Both conditions must hold: all the material worked through, AND every
    assessment on the course passed.

    A course with no assessment is decided on the material alone.
    """
    if enrollment.progress_percent < 100:
        return False

    assessments = enrollment.course.assessments.all()
    for assessment in assessments:
        passed = Attempt.objects.filter(
            assessment=assessment, learner=enrollment.learner, passed=True
        ).exists()
        if not passed:
            return False
    return True


def issue_certificate_if_earned(enrollment: Enrollment):
    """
    Issue a certificate, once.

    Called from two places -- after material is marked done, and after an
    assessment is submitted -- because either can be the step that completes
    the course. Returning early when one already exists is what makes it safe
    to call from both.
    """
    existing = Certificate.objects.filter(enrollment=enrollment).first()
    if existing:
        return existing

    if not has_earned_certificate(enrollment):
        return None

    if enrollment.status != EnrollmentStatus.COMPLETED:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = timezone.now()
        enrollment.save(update_fields=["status", "completed_at"])

    return Certificate.objects.create(
        enrollment=enrollment,
        serial_no=_next_serial(),
        verification_code=_generate_verification_code(),
    )
