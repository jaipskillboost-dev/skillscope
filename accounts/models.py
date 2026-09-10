"""
Who someone is, and which institution they belong to.

Only two models live here: Institution and User. Everything else -- courses,
skills, assessments -- lives in the learning app.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Role(models.TextChoices):
    """The four kinds of people who use SkillScope."""

    LEARNER = "LEARNER", "Learner"
    TRAINER = "TRAINER", "Trainer"
    INSTITUTE_ADMIN = "INSTITUTE_ADMIN", "Institute admin"
    PLATFORM_ADMIN = "PLATFORM_ADMIN", "Platform admin"


class InstitutionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending review"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class InstitutionType(models.TextChoices):
    UNIVERSITY = "UNIVERSITY", "University"
    COLLEGE = "COLLEGE", "College"
    TRAINING_CENTRE = "TRAINING_CENTRE", "Training centre"
    CORPORATE = "CORPORATE", "Corporate academy"
    GOVERNMENT = "GOVERNMENT", "Government body"


class Institution(models.Model):
    """
    An organisation that runs courses on SkillScope.

    An institution applies, and stays PENDING until a platform admin verifies
    it. Until then its admin cannot create courses and none of its courses
    appear in the public catalogue.
    """

    name = models.CharField(max_length=200)
    institution_type = models.CharField(
        max_length=20, choices=InstitutionType.choices, default=InstitutionType.TRAINING_CENTRE
    )
    registration_no = models.CharField(max_length=60, unique=True)
    description = models.TextField(blank=True)

    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)

    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    logo = models.ImageField(upload_to="institutions/logos/", blank=True, null=True)
    # Proof of registration, uploaded when applying. What the platform admin reviews.
    document = models.FileField(upload_to="institutions/documents/", blank=True, null=True)

    status = models.CharField(
        max_length=10, choices=InstitutionStatus.choices, default=InstitutionStatus.PENDING
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, blank=True, null=True,
        related_name="institutions_verified",
    )
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_verified(self):
        return self.status == InstitutionStatus.VERIFIED


class UserManager(BaseUserManager):
    """
    Creates users. Django's built-in manager expects a username; ours uses the
    email address instead, so it needs replacing.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("An email address is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("role", Role.LEARNER)
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", Role.PLATFORM_ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("full_name", "Platform administrator")
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """
    One account. The role decides what they can do; the institution decides
    whose data they can see.

    Platform admins have no institution -- they sit above all of them.
    Learners have no institution either; they enrol across the whole platform.
    """

    # Sign-in is by email, so the inherited username field is not used.
    username = None
    first_name = None
    last_name = None

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.LEARNER)
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, blank=True, null=True, related_name="members"
    )

    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="users/photos/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def short_name(self):
        """Just the first word of the name, for greetings."""
        return self.full_name.split()[0] if self.full_name else self.email

    @property
    def initials(self):
        parts = [p for p in self.full_name.split() if p]
        return "".join(p[0] for p in parts[:2]).upper() if parts else "?"

    # Convenience flags, so templates can say {% if user.is_trainer %} rather
    # than comparing role strings in three different places.
    @property
    def is_learner(self):
        return self.role == Role.LEARNER

    @property
    def is_trainer(self):
        return self.role == Role.TRAINER

    @property
    def is_institute_admin(self):
        return self.role == Role.INSTITUTE_ADMIN

    @property
    def is_platform_admin(self):
        return self.role == Role.PLATFORM_ADMIN

    @property
    def institution_verified(self):
        """An institute admin or trainer can only work once their institution is verified."""
        return self.institution is not None and self.institution.is_verified
