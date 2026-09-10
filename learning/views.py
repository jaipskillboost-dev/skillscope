"""
Courses, material, enrolment, assessments, certificates and notices.

The public pages at the top show only PUBLISHED courses from VERIFIED
institutions -- that pairing is what stops an unreviewed institution putting
anything in front of the public.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, OuterRef, Q, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Institution, InstitutionStatus, Role, User
from accounts.permissions import (
    get_scoped_object_or_404, institute_admin_required, learner_required,
    platform_admin_required, scope_courses, scope_resources, trainer_required,
)
from learning.forms import (
    AssessmentForm, CourseForm, FeedbackForm, QuestionForm, ResourceForm,
)
from learning.models import (
    Announcement, Assessment, Attempt, Certificate, Course, CourseStatus,
    Enrollment, Feedback, Resource, ResourceCompletion, Subject,
)
from learning.services import (
    AlreadyAttempted, DeadlinePassed, issue_certificate_if_earned, mark_attempt,
)


def public_courses():
    """
    The one definition of "a course the public may see".

    Used by every public page so the rule cannot drift apart between them.

    Each course also comes with its learner count and average rating already
    worked out, in this same query. Course cards show both, and asking for
    them one card at a time was thirty-seven queries for twelve courses.
    """
    # The average rating is a small query of its own, run once per course
    # inside the main one. Joining feedback directly would multiply its rows
    # by the enrolment rows and throw off the count below.
    ratings = (Feedback.objects.filter(course=OuterRef("pk"))
               .values("course")
               .annotate(avg=Avg("overall_rating"))
               .values("avg"))

    return Course.objects.filter(
        status=CourseStatus.PUBLISHED,
        institution__status=InstitutionStatus.VERIFIED,
    ).select_related("subject", "institution", "trainer").annotate(
        enrolled_total=Count("enrollments", distinct=True),
        rating_avg=Subquery(ratings),
    )


# ===========================================================================
# PUBLIC PAGES
# ===========================================================================

def home(request):
    notices = Announcement.objects.select_related("institution")[:6]
    courses = public_courses()

    return render(request, "public/home.html", {
        "notices": notices,
        "courses": courses[:6],
        "subjects": Subject.objects.annotate(
            n=Count("courses", filter=Q(courses__status=CourseStatus.PUBLISHED))
        )[:8],
        "course_count": courses.count(),
        "institution_count": Institution.objects.filter(
            status=InstitutionStatus.VERIFIED).count(),
        "learner_count": User.objects.filter(role=Role.LEARNER).count(),
        "certificate_count": Certificate.objects.count(),
    })


def course_catalog(request):
    courses = public_courses()

    subject_id = request.GET.get("subject")
    level = request.GET.get("level")
    query = (request.GET.get("q") or "").strip()

    if subject_id:
        courses = courses.filter(subject_id=subject_id)
    if level:
        courses = courses.filter(level=level)
    if query:
        courses = courses.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
            | Q(institution__name__icontains=query)
        )

    return render(request, "public/courses.html", {
        "courses": courses,
        "subjects": Subject.objects.all(),
        "levels": Course._meta.get_field("level").choices,
        "subject_id": subject_id or "",
        "level": level or "",
        "q": query,
    })


def course_detail(request, course_id):
    course = get_object_or_404(public_courses(), pk=course_id)

    enrollment = None
    if request.user.is_authenticated and request.user.is_learner:
        enrollment = Enrollment.objects.filter(course=course, learner=request.user).first()

    return render(request, "public/course_detail.html", {
        "course": course,
        "resources": course.resources.all(),
        "assessments": course.assessments.all(),
        "enrollment": enrollment,
        "feedback": course.feedback.select_related("learner")[:8],
        "rating": course.feedback.aggregate(v=Avg("overall_rating"))["v"],
        "learner_count": course.enrollments.count(),
    })


def subject_list(request):
    subjects = Subject.objects.annotate(
        course_count=Count("courses", filter=Q(courses__status=CourseStatus.PUBLISHED))
    )
    return render(request, "public/subjects.html", {"subjects": subjects})


def institution_list(request):
    institutions = Institution.objects.filter(
        status=InstitutionStatus.VERIFIED
    ).annotate(
        course_count=Count("courses", filter=Q(courses__status=CourseStatus.PUBLISHED))
    )
    return render(request, "public/institutions.html", {"institutions": institutions})


def verify_form(request):
    """Type a code by hand, for anyone who cannot scan the QR."""
    if request.method == "POST":
        code = (request.POST.get("code") or "").strip().upper()
        if code:
            return redirect("verify_certificate", code=code)
        messages.error(request, "Enter the code printed on the certificate.")
    return render(request, "public/verify_form.html")


def verify_certificate(request, code):
    """
    Public, and deliberately needs no sign-in -- an employer checking a
    certificate has no reason to have an account.
    """
    certificate = Certificate.objects.filter(
        verification_code=code.strip().upper()
    ).select_related(
        "enrollment__learner", "enrollment__course__institution",
        "enrollment__course__subject", "enrollment__course__trainer",
    ).first()

    return render(request, "public/verify.html", {
        "certificate": certificate,
        "code": code,
    })


# ===========================================================================
# LEARNER
# ===========================================================================

@learner_required
def my_learning(request):
    enrollments = Enrollment.objects.filter(learner=request.user).select_related(
        "course", "course__subject", "course__institution", "course__trainer"
    )
    return render(request, "learner/my_learning.html", {"enrollments": enrollments})


@learner_required
def enroll(request, course_id):
    course = get_object_or_404(public_courses(), pk=course_id)
    if request.method != "POST":
        return redirect("course_detail", course_id=course.id)

    enrollment, created = Enrollment.objects.get_or_create(
        course=course, learner=request.user
    )
    if created:
        messages.success(request, f"You are enrolled on {course.title}.")
    return redirect("course_learn", enrollment_id=enrollment.id)


@learner_required
def course_learn(request, enrollment_id):
    """The learning page: material list, progress, and any assessments."""
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("course", "course__institution", "course__trainer"),
        pk=enrollment_id, learner=request.user,
    )
    done_ids = set(
        enrollment.completions.values_list("resource_id", flat=True)
    )
    attempts = {
        a.assessment_id: a
        for a in Attempt.objects.filter(
            learner=request.user, assessment__course=enrollment.course,
            submitted_at__isnull=False,
        )
    }

    return render(request, "learner/course_learn.html", {
        "enrollment": enrollment,
        "course": enrollment.course,
        "resources": enrollment.course.resources.all(),
        "done_ids": done_ids,
        "assessments": enrollment.course.assessments.all(),
        "attempts": attempts,
        "certificate": Certificate.objects.filter(enrollment=enrollment).first(),
        "has_feedback": Feedback.objects.filter(
            course=enrollment.course, learner=request.user).exists(),
    })


@learner_required
def mark_resource_done(request, enrollment_id, resource_id):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, learner=request.user)
    if request.method != "POST":
        return redirect("course_learn", enrollment_id=enrollment.id)

    resource = get_object_or_404(Resource, pk=resource_id, course=enrollment.course)
    ResourceCompletion.objects.get_or_create(enrollment=enrollment, resource=resource)
    enrollment.recalculate_progress()

    # Finishing the last item can be what earns the certificate, so check here
    # as well as after an assessment.
    certificate = issue_certificate_if_earned(enrollment)
    if certificate:
        messages.success(request, "Course complete. Your certificate is ready.")

    return redirect("course_learn", enrollment_id=enrollment.id)


@learner_required
def assessment_take(request, assessment_id):
    assessment = get_object_or_404(
        Assessment.objects.select_related("course"), pk=assessment_id
    )
    if not Enrollment.objects.filter(course=assessment.course, learner=request.user).exists():
        raise Http404("You are not enrolled on this course.")

    existing = Attempt.objects.filter(
        assessment=assessment, learner=request.user, submitted_at__isnull=False
    ).first()
    if existing:
        return redirect("attempt_result", attempt_id=existing.id)

    if not assessment.is_open:
        messages.error(request, "That assessment has closed.")
        return redirect("course_detail", course_id=assessment.course_id)

    return render(request, "learner/assessment_take.html", {
        "assessment": assessment,
        # .only() keeps the answer key out of the objects handed to the
        # template, so it cannot be printed into the page by accident.
        "questions": assessment.questions.only(
            "id", "question_text", "option_a", "option_b", "option_c", "option_d",
            "marks", "position", "assessment",
        ),
    })


@learner_required
def assessment_submit(request, assessment_id):
    assessment = get_object_or_404(Assessment, pk=assessment_id)
    if request.method != "POST":
        return redirect("assessment_take", assessment_id=assessment.id)

    if not Enrollment.objects.filter(course=assessment.course, learner=request.user).exists():
        raise Http404("You are not enrolled on this course.")

    answers = {
        key.replace("q_", ""): value
        for key, value in request.POST.items()
        if key.startswith("q_")
    }

    try:
        attempt = mark_attempt(assessment, request.user, answers)
    except DeadlinePassed:
        messages.error(request, "That assessment closed before your answers arrived.")
        return redirect("course_detail", course_id=assessment.course_id)
    except AlreadyAttempted:
        messages.info(request, "You have already submitted this assessment.")
        return redirect("course_detail", course_id=assessment.course_id)

    return redirect("attempt_result", attempt_id=attempt.id)


@learner_required
def attempt_result(request, attempt_id):
    attempt = get_object_or_404(
        Attempt.objects.select_related("assessment", "assessment__course"),
        pk=attempt_id, learner=request.user,
    )
    return render(request, "learner/attempt_result.html", {
        "attempt": attempt,
        "answers": attempt.answers.select_related("question"),
        "certificate": Certificate.objects.filter(
            enrollment__course=attempt.assessment.course,
            enrollment__learner=request.user,
        ).first(),
    })


@learner_required
def give_feedback(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, learner=request.user)
    existing = Feedback.objects.filter(course=enrollment.course, learner=request.user).first()
    if existing:
        messages.info(request, "You have already reviewed this course.")
        return redirect("course_learn", enrollment_id=enrollment.id)

    form = FeedbackForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        feedback = form.save(commit=False)
        feedback.course = enrollment.course
        feedback.learner = request.user
        feedback.save()
        messages.success(request, "Thank you for the feedback.")
        return redirect("course_learn", enrollment_id=enrollment.id)

    return render(request, "learner/feedback_form.html",
                  {"form": form, "enrollment": enrollment})


@learner_required
def my_certificates(request):
    certificates = Certificate.objects.filter(
        enrollment__learner=request.user
    ).select_related("enrollment__course", "enrollment__course__institution")
    return render(request, "learner/certificates.html", {"certificates": certificates})


@login_required
def certificate_view(request, certificate_id):
    """The printable certificate. Only the person it belongs to can open it."""
    certificate = get_object_or_404(
        Certificate.objects.select_related(
            "enrollment__course__institution", "enrollment__course__trainer",
            "enrollment__course__subject", "enrollment__learner",
        ),
        pk=certificate_id, enrollment__learner=request.user,
    )
    return render(request, "learner/certificate.html", {"certificate": certificate})


# ===========================================================================
# TRAINER
# ===========================================================================

@trainer_required
def trainer_courses(request):
    courses = scope_courses(request.user, Course.objects.all()).select_related(
        "subject", "institution"
    ).annotate(learners=Count("enrollments", distinct=True))
    return render(request, "trainer/courses.html", {"courses": courses})


@trainer_required
def trainer_course_manage(request, course_id):
    """
    Material and assessments for one course.

    get_scoped_object_or_404 filters to this trainer's own courses first, so
    another trainer's course id gives "not found" rather than a page.
    """
    course = get_scoped_object_or_404(request.user, Course, scope_courses, course_id)
    return render(request, "trainer/course_manage.html", {
        "course": course,
        "resources": course.resources.all(),
        "assessments": course.assessments.annotate(n=Count("questions")),
        "resource_form": ResourceForm(),
        "assessment_form": AssessmentForm(),
        "enrollments": course.enrollments.select_related("learner"),
    })


@trainer_required
def trainer_add_resource(request, course_id):
    course = get_scoped_object_or_404(request.user, Course, scope_courses, course_id)
    if request.method != "POST":
        return redirect("trainer_course_manage", course_id=course.id)

    form = ResourceForm(request.POST, request.FILES)
    if form.is_valid():
        resource = form.save(commit=False)
        resource.course = course
        resource.institution = course.institution
        resource.subject = course.subject
        resource.uploaded_by = request.user
        resource.save()
        # New material changes the denominator, so everyone's progress moves.
        for enrollment in course.enrollments.all():
            enrollment.recalculate_progress()
        messages.success(request, f"'{resource.title}' uploaded.")
    else:
        messages.error(request, next(iter(form.errors.values()))[0])

    return redirect("trainer_course_manage", course_id=course.id)


@trainer_required
def trainer_delete_resource(request, resource_id):
    resource = get_scoped_object_or_404(request.user, Resource, scope_resources, resource_id)
    if request.method != "POST":
        return redirect("trainer_library")

    course_id = resource.course_id
    resource.delete()
    if course_id:
        for enrollment in Enrollment.objects.filter(course_id=course_id):
            enrollment.recalculate_progress()
        messages.success(request, "Material removed.")
        return redirect("trainer_course_manage", course_id=course_id)

    messages.success(request, "Library item removed.")
    return redirect("trainer_library")


@trainer_required
def trainer_library(request):
    """
    The institution's shared library: material not tied to any one course.
    Every trainer in the institution can see it, which is the point.
    """
    resources = scope_resources(request.user, Resource.objects.filter(course__isnull=True))
    resources = resources.select_related("subject", "uploaded_by")

    subject_id = request.GET.get("subject")
    if subject_id:
        resources = resources.filter(subject_id=subject_id)

    if request.method == "POST":
        form = ResourceForm(request.POST, request.FILES)
        subject = get_object_or_404(Subject, pk=request.POST.get("subject_id"))
        if form.is_valid():
            item = form.save(commit=False)
            item.course = None
            item.institution = request.user.institution
            item.subject = subject
            item.uploaded_by = request.user
            item.save()
            messages.success(request, f"'{item.title}' added to the library.")
            return redirect("trainer_library")
        messages.error(request, next(iter(form.errors.values()))[0])
    else:
        form = ResourceForm()

    return render(request, "trainer/library.html", {
        "resources": resources,
        "subjects": Subject.objects.all(),
        "subject_id": subject_id or "",
        "form": form,
    })


@trainer_required
def trainer_create_assessment(request, course_id):
    course = get_scoped_object_or_404(request.user, Course, scope_courses, course_id)
    if request.method != "POST":
        return redirect("trainer_course_manage", course_id=course.id)

    form = AssessmentForm(request.POST)
    if form.is_valid():
        assessment = form.save(commit=False)
        assessment.course = course
        assessment.subject = course.subject
        assessment.trainer = request.user
        assessment.save()
        messages.success(request, "Assessment created. Now add some questions.")
        return redirect("trainer_assessment_manage", assessment_id=assessment.id)

    messages.error(request, next(iter(form.errors.values()))[0])
    return redirect("trainer_course_manage", course_id=course.id)


@trainer_required
def trainer_assessment_manage(request, assessment_id):
    """Questions, results, and which questions people got wrong most often."""
    assessment = get_object_or_404(
        Assessment.objects.select_related("course"), pk=assessment_id, trainer=request.user
    )
    questions = assessment.questions.all()
    attempts = assessment.attempts.filter(
        submitted_at__isnull=False
    ).select_related("learner")

    enrolled = assessment.course.enrollments.count()
    attempted = attempts.count()

    # Per-question difficulty: the questions most people got wrong are the ones
    # worth rewriting, or reteaching.
    analysis = []
    for question in questions:
        answers = question.answers.filter(attempt__submitted_at__isnull=False)
        total = answers.count()
        correct = answers.filter(is_correct=True).count()
        analysis.append({
            "question": question,
            "total": total,
            "correct": correct,
            "percent": round(correct * 100 / total) if total else None,
        })

    return render(request, "trainer/assessment_manage.html", {
        "assessment": assessment,
        "questions": questions,
        "question_form": QuestionForm(),
        "attempts": attempts,
        "enrolled": enrolled,
        "attempted": attempted,
        "participation": round(attempted * 100 / enrolled) if enrolled else 0,
        "passed": attempts.filter(passed=True).count(),
        "average": attempts.aggregate(v=Avg("percentage"))["v"],
        "analysis": analysis,
    })


@trainer_required
def trainer_add_question(request, assessment_id):
    assessment = get_object_or_404(Assessment, pk=assessment_id, trainer=request.user)
    if request.method != "POST":
        return redirect("trainer_assessment_manage", assessment_id=assessment.id)

    form = QuestionForm(request.POST)
    if form.is_valid():
        question = form.save(commit=False)
        question.assessment = assessment
        question.position = assessment.questions.count() + 1
        question.save()
        messages.success(request, "Question added.")
    else:
        messages.error(request, next(iter(form.errors.values()))[0])

    return redirect("trainer_assessment_manage", assessment_id=assessment.id)


# ===========================================================================
# INSTITUTE ADMIN
# ===========================================================================

@institute_admin_required
def institute_courses(request):
    courses = scope_courses(request.user, Course.objects.all()).select_related(
        "subject", "trainer"
    ).annotate(learners=Count("enrollments", distinct=True))
    return render(request, "institute/courses.html", {"courses": courses})


@institute_admin_required
def institute_course_create(request):
    form = CourseForm(request.POST or None, request.FILES or None,
                      institution=request.user.institution)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        # Taken from the signed-in admin, never from the form, so a course
        # cannot be created inside another institution.
        course.institution = request.user.institution
        course.created_by = request.user
        course.save()
        messages.success(request, f"'{course.title}' created.")
        return redirect("institute_courses")

    return render(request, "institute/course_form.html", {"form": form, "course": None})


@institute_admin_required
def institute_course_edit(request, course_id):
    course = get_scoped_object_or_404(request.user, Course, scope_courses, course_id)
    form = CourseForm(request.POST or None, request.FILES or None,
                      instance=course, institution=request.user.institution)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Course updated.")
        return redirect("institute_courses")

    return render(request, "institute/course_form.html", {"form": form, "course": course})


@institute_admin_required
def institute_learners(request):
    """Everyone enrolled on any of this institution's courses."""
    enrollments = Enrollment.objects.filter(
        course__institution=request.user.institution
    ).select_related("learner", "course", "course__subject")

    return render(request, "institute/learners.html", {
        "enrollments": enrollments,
        "total": enrollments.count(),
        "completed": enrollments.filter(status="COMPLETED").count(),
    })


# ===========================================================================
# PLATFORM ADMIN
# ===========================================================================

@platform_admin_required
def platform_announcements(request):
    """Publish a notice to the public home page."""
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        body = (request.POST.get("body") or "").strip()
        kind = request.POST.get("announcement_type") or "ANNOUNCEMENT"

        if not title or not body:
            messages.error(request, "A notice needs both a title and a message.")
        else:
            Announcement.objects.create(
                announcement_type=kind, title=title, body=body,
                posted_by=request.user, pinned=bool(request.POST.get("pinned")),
            )
            messages.success(request, "Published to the home page.")
            return redirect("platform_announcements")

    return render(request, "platform/announcements.html", {
        "announcements": Announcement.objects.select_related("posted_by"),
        "types": Announcement._meta.get_field("announcement_type").choices,
    })
