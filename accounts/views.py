"""
Signing in, signing up, profiles, and the two admin areas that deal with
people and institutions.

Course and assessment pages live in learning/views.py.
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.forms import (
    ExperienceForm, InstituteAdminRegisterForm, InstitutionApplicationForm,
    LearnerRegisterForm, LoginForm, ProfileForm, QualificationForm,
    TrainerCreateForm, UserCertificateForm, UserSkillForm,
)
from accounts.models import Institution, InstitutionStatus, Role, User
from accounts.permissions import (
    institute_admin_required, platform_admin_required, scope_users,
)
from learning.models import (
    Assessment, Attempt, Certificate, Course, CourseStatus, Enrollment,
    Experience, Qualification, UserCertificate, UserSkill,
)


# ===========================================================================
# AUTHENTICATION
# ===========================================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.cleaned_data["user"])
        return redirect(request.GET.get("next") or "dashboard")

    return render(request, "auth/login.html", {"form": form})


def logout_view(request):
    # Only ever sign out on a POST, so a stray link or a prefetching browser
    # cannot log somebody out without them asking.
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have been signed out.")
    return redirect("home")


def register_choice(request):
    """Ask which kind of account before showing a form."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "auth/register_choice.html")


def register_learner(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LearnerRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to SkillScope, {user.full_name.split()[0]}.")
        return redirect("dashboard")

    return render(request, "auth/register_learner.html", {"form": form})


def register_institution(request):
    """
    Creates the institution and its first admin together.

    Both are saved inside one transaction: an institution with no admin, or an
    admin with no institution, would both be stranded records that nobody
    could sign in to fix.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    inst_form = InstitutionApplicationForm(request.POST or None, request.FILES or None)
    admin_form = InstituteAdminRegisterForm(request.POST or None)

    if request.method == "POST" and inst_form.is_valid() and admin_form.is_valid():
        with transaction.atomic():
            institution = inst_form.save()  # status defaults to PENDING
            user = admin_form.save(commit=False)
            user.role = Role.INSTITUTE_ADMIN
            user.institution = institution
            user.set_password(admin_form.cleaned_data["password"])
            user.save()
        login(request, user)
        messages.info(
            request,
            "Your application has been submitted. A platform administrator will review it.",
        )
        return redirect("awaiting_verification")

    return render(request, "auth/register_institution.html",
                  {"inst_form": inst_form, "admin_form": admin_form})


@login_required
def awaiting_verification(request):
    """
    Where institute admins and trainers land while their institution is still
    pending. They can sign in, but this is all they can reach.
    """
    if request.user.institution_verified:
        return redirect("dashboard")
    return render(request, "auth/awaiting_verification.html",
                  {"institution": request.user.institution})


def denied(request):
    return render(request, "auth/denied.html", status=403)


# ===========================================================================
# DASHBOARD -- one address, four different pages
# ===========================================================================

@login_required
def dashboard(request):
    user = request.user

    if user.is_learner:
        return _learner_dashboard(request)
    if user.is_trainer:
        if not user.institution_verified:
            return redirect("awaiting_verification")
        return _trainer_dashboard(request)
    if user.is_institute_admin:
        if not user.institution_verified:
            return redirect("awaiting_verification")
        return _institute_dashboard(request)
    if user.is_platform_admin:
        return _platform_dashboard(request)

    return redirect("home")


def _learner_dashboard(request):
    enrollments = (
        Enrollment.objects.filter(learner=request.user)
        .select_related("course", "course__subject", "course__institution")
    )
    upcoming = (
        Assessment.objects.filter(
            course__enrollments__learner=request.user, deadline__gte=timezone.now()
        )
        .select_related("course")
        .distinct()
        .order_by("deadline")[:5]
    )
    return render(request, "learner/dashboard.html", {
        "enrollments": enrollments[:6],
        "total_enrolled": enrollments.count(),
        "in_progress": enrollments.filter(status="ENROLLED").count(),
        "completed": enrollments.filter(status="COMPLETED").count(),
        "certificates": Certificate.objects.filter(enrollment__learner=request.user).count(),
        "upcoming": upcoming,
    })


def _trainer_dashboard(request):
    courses = Course.objects.filter(trainer=request.user).select_related("subject")
    learner_count = Enrollment.objects.filter(course__trainer=request.user).count()
    assessments = Assessment.objects.filter(trainer=request.user)
    return render(request, "trainer/dashboard.html", {
        "courses": courses[:6],
        "total_courses": courses.count(),
        "published": courses.filter(status=CourseStatus.PUBLISHED).count(),
        "learner_count": learner_count,
        "assessment_count": assessments.count(),
        "open_assessments": assessments.filter(deadline__gte=timezone.now()).count(),
        "recent_attempts": (
            Attempt.objects.filter(assessment__trainer=request.user, submitted_at__isnull=False)
            .select_related("learner", "assessment")[:8]
        ),
    })


def _institute_dashboard(request):
    institution = request.user.institution
    courses = Course.objects.filter(institution=institution)
    enrollments = Enrollment.objects.filter(course__institution=institution)

    # Enrolments per course, for the chart.
    per_course = list(
        courses.annotate(n=Count("enrollments")).values("title", "n").order_by("-n")[:8]
    )

    return render(request, "institute/dashboard.html", {
        "institution": institution,
        "total_courses": courses.count(),
        "published": courses.filter(status=CourseStatus.PUBLISHED).count(),
        "unassigned": courses.filter(trainer__isnull=True).count(),
        "trainer_count": User.objects.filter(institution=institution, role=Role.TRAINER).count(),
        "enrollment_count": enrollments.count(),
        "completed_count": enrollments.filter(status="COMPLETED").count(),
        "certificate_count": Certificate.objects.filter(
            enrollment__course__institution=institution).count(),
        "chart_labels": [c["title"][:22] for c in per_course],
        "chart_values": [c["n"] for c in per_course],
        "recent_courses": courses.select_related("subject", "trainer")[:6],
    })


def _platform_dashboard(request):
    institutions = Institution.objects.all()
    courses = Course.objects.all()
    enrollments = Enrollment.objects.all()

    per_institution = list(
        institutions.filter(status=InstitutionStatus.VERIFIED)
        .annotate(n=Count("courses__enrollments"))
        .values("name", "n").order_by("-n")[:8]
    )

    return render(request, "platform/dashboard.html", {
        "institution_count": institutions.count(),
        "pending_count": institutions.filter(status=InstitutionStatus.PENDING).count(),
        "verified_count": institutions.filter(status=InstitutionStatus.VERIFIED).count(),
        "user_count": User.objects.count(),
        "learner_count": User.objects.filter(role=Role.LEARNER).count(),
        "trainer_count": User.objects.filter(role=Role.TRAINER).count(),
        "course_count": courses.count(),
        "enrollment_count": enrollments.count(),
        "certificate_count": Certificate.objects.count(),
        "attempt_count": Attempt.objects.filter(submitted_at__isnull=False).count(),
        "pending_institutions": institutions.filter(status=InstitutionStatus.PENDING)[:5],
        "chart_labels": [i["name"][:22] for i in per_institution],
        "chart_values": [i["n"] for i in per_institution],
    })


# ===========================================================================
# PROFILE
# ===========================================================================

@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")

    return render(request, "profile/profile.html", {
        "form": form,
        "qualification_form": QualificationForm(),
        "experience_form": ExperienceForm(),
        "skill_form": UserSkillForm(),
        "certificate_form": UserCertificateForm(),
        "qualifications": request.user.qualifications.all(),
        "experiences": request.user.experiences.select_related("subject"),
        "skills": request.user.skills.select_related("subject"),
        "certificates": request.user.uploaded_certificates.all(),
    })


def _add_profile_item(request, form_class, label):
    """The four 'add something to my profile' views differ only in the form."""
    if request.method != "POST":
        return redirect("profile")
    form = form_class(request.POST, request.FILES or None)
    if form.is_valid():
        item = form.save(commit=False)
        item.user = request.user
        item.save()
        messages.success(request, f"{label} added.")
    else:
        first_error = next(iter(form.errors.values()))[0]
        messages.error(request, f"Could not add {label.lower()}: {first_error}")
    return redirect("profile")


@login_required
def add_qualification(request):
    return _add_profile_item(request, QualificationForm, "Qualification")


@login_required
def add_experience(request):
    return _add_profile_item(request, ExperienceForm, "Experience")


@login_required
def add_skill(request):
    return _add_profile_item(request, UserSkillForm, "Skill")


@login_required
def add_user_certificate(request):
    return _add_profile_item(request, UserCertificateForm, "Certificate")


@login_required
def delete_profile_item(request, kind, pk):
    models_by_kind = {
        "qualification": Qualification,
        "experience": Experience,
        "skill": UserSkill,
        "certificate": UserCertificate,
    }
    model = models_by_kind.get(kind)
    if model is None or request.method != "POST":
        return redirect("profile")
    # Filtering by user as well as pk means you cannot delete someone else's row.
    get_object_or_404(model, pk=pk, user=request.user).delete()
    messages.success(request, "Removed.")
    return redirect("profile")


# ===========================================================================
# INSTITUTE ADMIN -- trainers
# ===========================================================================

@institute_admin_required
def institute_trainers(request):
    trainers = (
        scope_users(request.user, User.objects.filter(role=Role.TRAINER))
        .annotate(course_count=Count("courses_teaching"))
    )
    return render(request, "institute/trainers.html", {"trainers": trainers})


@institute_admin_required
def institute_trainer_create(request):
    """
    Trainers do not sign themselves up. The institute admin creates the
    account, and the new trainer is attached to that admin's institution --
    never to one chosen in the form, which is what stops an admin from
    creating staff inside somebody else's institution.
    """
    form = TrainerCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        trainer = form.save(commit=False)
        trainer.role = Role.TRAINER
        trainer.institution = request.user.institution
        trainer.set_password(form.cleaned_data["password"])
        trainer.save()
        messages.success(
            request,
            f"Trainer account created for {trainer.full_name}. "
            f"Sign-in email: {trainer.email} - password: {form.cleaned_data['password']}",
        )
        return redirect("institute_trainers")

    return render(request, "institute/trainer_form.html", {"form": form})


# ===========================================================================
# PLATFORM ADMIN -- institutions and users
# ===========================================================================

@platform_admin_required
def platform_institutions(request):
    status = request.GET.get("status", "")
    institutions = Institution.objects.annotate(
        member_count=Count("members", distinct=True),
        course_count=Count("courses", distinct=True),
    )
    if status in InstitutionStatus.values:
        institutions = institutions.filter(status=status)

    return render(request, "platform/institutions.html", {
        "institutions": institutions,
        "status": status,
        "statuses": InstitutionStatus.choices,
        "pending_count": Institution.objects.filter(status=InstitutionStatus.PENDING).count(),
    })


@platform_admin_required
def platform_institution_review(request, institution_id):
    """Verify or reject one application."""
    institution = get_object_or_404(Institution, pk=institution_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "verify":
            institution.status = InstitutionStatus.VERIFIED
            institution.verified_at = timezone.now()
            institution.verified_by = request.user
            institution.rejection_reason = ""
            institution.save()
            messages.success(request, f"{institution.name} is now verified.")
            return redirect("platform_institutions")

        if action == "reject":
            reason = (request.POST.get("rejection_reason") or "").strip()
            if not reason:
                messages.error(request, "Give a reason so the applicant knows what to fix.")
            else:
                institution.status = InstitutionStatus.REJECTED
                institution.rejection_reason = reason
                institution.verified_at = None
                institution.save()
                messages.success(request, f"{institution.name} was rejected.")
                return redirect("platform_institutions")

    return render(request, "platform/institution_review.html", {
        "institution": institution,
        "members": institution.members.all(),
        "courses": institution.courses.select_related("subject", "trainer"),
    })


@platform_admin_required
def platform_users(request):
    role = request.GET.get("role", "")
    query = (request.GET.get("q") or "").strip()

    users = User.objects.select_related("institution")
    if role in Role.values:
        users = users.filter(role=role)
    if query:
        users = users.filter(Q(full_name__icontains=query) | Q(email__icontains=query))

    return render(request, "platform/users.html", {
        "users": users[:200],
        "total": users.count(),
        "role": role,
        "roles": Role.choices,
        "q": query,
    })
