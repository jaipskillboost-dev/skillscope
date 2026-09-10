"""
Who is allowed to do what, and whose data they are allowed to see.

Two separate ideas live here, and both matter:

1. ROLE  -- is this person a trainer at all?
2. TENANT -- is this course one of *their institution's* courses?

The second is the one that is easy to forget. SkillScope hosts many
institutions at once, so a check like "is this user a trainer" is not enough:
without also filtering by institution, one institute's admin could open
another institute's learner list by editing the number in the address bar.

Every view that touches institution-owned data goes through the helpers at the
bottom of this file rather than calling Course.objects.get() directly, so the
check happens once, here, instead of being re-typed in thirty views.
"""

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect

from accounts.models import Role


# ---------------------------------------------------------------------------
# ROLE CHECKS
# ---------------------------------------------------------------------------

def role_required(*roles):
    """
    Only let people with one of these roles through.

    Used as:  @role_required(Role.TRAINER)
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.role not in roles:
                return redirect("denied")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


learner_required = role_required(Role.LEARNER)
platform_admin_required = role_required(Role.PLATFORM_ADMIN)


def institution_member_required(view):
    """
    For trainers and institute admins.

    As well as the role, this checks the institution has actually been
    verified by a platform admin. An unverified institution's staff can sign
    in, but they land on the holding page and can do nothing else -- which is
    what makes the verification step visible rather than a hidden flag.
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role not in (Role.TRAINER, Role.INSTITUTE_ADMIN):
            return redirect("denied")
        if not request.user.institution_verified:
            return redirect("awaiting_verification")
        return view(request, *args, **kwargs)

    return wrapper


def trainer_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role != Role.TRAINER:
            return redirect("denied")
        if not request.user.institution_verified:
            return redirect("awaiting_verification")
        return view(request, *args, **kwargs)

    return wrapper


def institute_admin_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role != Role.INSTITUTE_ADMIN:
            return redirect("denied")
        if not request.user.institution_verified:
            return redirect("awaiting_verification")
        return view(request, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# TENANT SCOPING
#
# These narrow a queryset to what this particular user is entitled to see.
# Views call these instead of the plain manager.
# ---------------------------------------------------------------------------

def scope_courses(user, queryset):
    """
    Narrow a Course queryset to the ones this user may work with.

    Platform admin   -> every course on the platform
    Institute admin  -> every course belonging to their institution
    Trainer          -> only the courses they have been assigned to teach
    Anyone else      -> nothing
    """
    if user.is_platform_admin:
        return queryset
    if user.is_institute_admin:
        return queryset.filter(institution=user.institution)
    if user.is_trainer:
        return queryset.filter(institution=user.institution, trainer=user)
    return queryset.none()


def scope_resources(user, queryset):
    """Same idea for study material."""
    if user.is_platform_admin:
        return queryset
    if user.is_institute_admin or user.is_trainer:
        return queryset.filter(institution=user.institution)
    return queryset.none()


def scope_users(user, queryset):
    """Same idea for people."""
    if user.is_platform_admin:
        return queryset
    if user.is_institute_admin:
        return queryset.filter(institution=user.institution)
    return queryset.none()


def get_scoped_object_or_404(user, model, scoper, pk):
    """
    Fetch one row, but only from the rows this user is allowed to see.

    Fetching then checking would leak whether a row exists at all. Filtering
    first means another institution's course is simply "not found", which is
    both safer and the honest answer.
    """
    queryset = scoper(user, model.objects.all())
    return get_object_or_404(queryset, pk=pk)


def require_own_institution(user, obj):
    """
    Last line of defence for objects reached indirectly.

    Raises rather than redirecting, because reaching here means a bug, not an
    ordinary user mistake.
    """
    if user.is_platform_admin:
        return
    if getattr(obj, "institution_id", None) != user.institution_id:
        raise PermissionDenied("That belongs to another institution.")
