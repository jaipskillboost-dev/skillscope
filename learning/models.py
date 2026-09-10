"""
Everything from a subject to a certificate.

The profile records (qualification, experience, skill, certificate) live here
rather than in the accounts app because three of them point at a Subject, and
keeping a model next to the thing it points at avoids a circular import
between the two apps.

Sections, in order:
    1. Subjects
    2. Profile records
    3. Courses and material
    4. Enrolment and progress
    5. Assessments
    6. Certificates
    7. Feedback and announcements
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


# ===========================================================================
# 1. SUBJECTS
# ===========================================================================

class Subject(models.Model):
    """
    A field of study. Courses belong to one, and so do skills -- which is what
    lets SkillScope work out who is qualified to teach what.
    """

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, blank=True, help_text="Bootstrap icon name")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ===========================================================================
# 2. PROFILE RECORDS
# ===========================================================================

class Qualification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="qualifications"
    )
    degree = models.CharField(max_length=150)
    institution_name = models.CharField(max_length=200)
    year_of_passing = models.PositiveIntegerField()
    percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ["-year_of_passing"]

    def __str__(self):
        return f"{self.degree} ({self.year_of_passing})"


class Experience(models.Model):
    """
    Work history. The subject tag is what makes this count towards a trainer's
    competency score, so it is required rather than optional.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="experiences"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="experiences")
    organisation = models.CharField(max_length=200)
    designation = models.CharField(max_length=150)
    from_year = models.PositiveIntegerField()
    to_year = models.PositiveIntegerField(blank=True, null=True)
    currently_working = models.BooleanField(default=False)

    class Meta:
        ordering = ["-from_year"]

    def __str__(self):
        return f"{self.designation} at {self.organisation}"

    @property
    def years(self):
        end = timezone.now().year if self.currently_working or not self.to_year else self.to_year
        return max(0, end - self.from_year)


class UserSkill(models.Model):
    """
    A skill someone claims, rated 1 to 5. Together with Experience and course
    feedback, this is one of the three inputs to the competency score.
    """

    PROFICIENCY_CHOICES = [
        (1, "Beginner"),
        (2, "Basic"),
        (3, "Intermediate"),
        (4, "Advanced"),
        (5, "Expert"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="skills"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="skills")
    skill_name = models.CharField(max_length=120)
    proficiency = models.PositiveSmallIntegerField(choices=PROFICIENCY_CHOICES, default=3)
    years_experience = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    class Meta:
        ordering = ["-proficiency", "skill_name"]

    def __str__(self):
        return f"{self.skill_name} ({self.get_proficiency_display()})"


class UserCertificate(models.Model):
    """A credential someone earned elsewhere and uploaded to their profile."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_certificates"
    )
    title = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200)
    issued_date = models.DateField()
    file = models.FileField(upload_to="users/certificates/", blank=True, null=True)

    class Meta:
        ordering = ["-issued_date"]

    def __str__(self):
        return self.title


# ===========================================================================
# 3. COURSES AND MATERIAL
# ===========================================================================

class CourseLevel(models.TextChoices):
    BEGINNER = "BEGINNER", "Beginner"
    INTERMEDIATE = "INTERMEDIATE", "Intermediate"
    ADVANCED = "ADVANCED", "Advanced"


class CourseStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED = "ARCHIVED", "Archived"


class Course(models.Model):
    """
    A course belongs to an institution, and the institute admin assigns a
    trainer to it. A course with no trainer yet cannot have material added --
    there is nobody to add it.
    """

    institution = models.ForeignKey(
        "accounts.Institution", on_delete=models.CASCADE, related_name="courses"
    )
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="courses")
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="courses_teaching",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="courses_created",
    )

    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    level = models.CharField(
        max_length=15, choices=CourseLevel.choices, default=CourseLevel.BEGINNER
    )
    duration_hours = models.PositiveIntegerField(default=10)
    cover_image = models.ImageField(upload_to="courses/covers/", blank=True, null=True)
    status = models.CharField(
        max_length=10, choices=CourseStatus.choices, default=CourseStatus.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.title}"

    @property
    def is_published(self):
        return self.status == CourseStatus.PUBLISHED

    @property
    def enrolled_count(self):
        return self.enrollments.count()

    @property
    def average_rating(self):
        result = self.feedback.aggregate(models.Avg("overall_rating"))["overall_rating__avg"]
        return round(result, 1) if result else None


class ResourceType(models.TextChoices):
    VIDEO = "VIDEO", "Recorded lecture"
    PPT = "PPT", "Presentation"
    PDF = "PDF", "PDF document"
    DOC = "DOC", "Document"
    LINK = "LINK", "External link"


class Resource(models.Model):
    """
    A piece of study material.

    A resource attached to a course is course material. A resource with no
    course is a standalone item in that institution's trainer library -- one
    table serves both, which is why `course` may be null.
    """

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, blank=True, null=True, related_name="resources"
    )
    institution = models.ForeignKey(
        "accounts.Institution", on_delete=models.CASCADE, related_name="resources"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="resources")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="resources_uploaded",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=10, choices=ResourceType.choices)
    file = models.FileField(upload_to="resources/", blank=True, null=True)
    link_url = models.URLField(blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.title

    @property
    def is_library_item(self):
        return self.course_id is None


# ===========================================================================
# 4. ENROLMENT AND PROGRESS
# ===========================================================================

class EnrollmentStatus(models.TextChoices):
    ENROLLED = "ENROLLED", "Enrolled"
    COMPLETED = "COMPLETED", "Completed"


class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    status = models.CharField(
        max_length=10, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ENROLLED
    )
    progress_percent = models.PositiveSmallIntegerField(default=0)
    enrolled_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(fields=["course", "learner"], name="unique_enrollment")
        ]

    def __str__(self):
        return f"{self.learner.full_name} - {self.course.title}"

    def recalculate_progress(self):
        """Progress is simply how much of the course material has been marked done."""
        total = self.course.resources.count()
        if total == 0:
            self.progress_percent = 0
        else:
            done = self.completions.count()
            self.progress_percent = round(done * 100 / total)

        if self.progress_percent >= 100 and self.status != EnrollmentStatus.COMPLETED:
            self.status = EnrollmentStatus.COMPLETED
            self.completed_at = timezone.now()

        self.save(update_fields=["progress_percent", "status", "completed_at"])
        return self.progress_percent


class ResourceCompletion(models.Model):
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="completions"
    )
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="completions")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "resource"], name="unique_resource_completion"
            )
        ]


# ===========================================================================
# 5. ASSESSMENTS
# ===========================================================================

class Assessment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assessments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="assessments")
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="assessments_created",
    )

    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    deadline = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    pass_percent = models.PositiveSmallIntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        return timezone.now() <= self.deadline

    @property
    def total_marks(self):
        return sum(q.marks for q in self.questions.all())


class Question(models.Model):
    """
    One multiple-choice question. The four options are columns rather than a
    separate table -- an MCQ always has exactly four, so a join would add
    complexity without adding anything.

    correct_option is never sent to the browser. Marking reads it here.
    """

    OPTION_CHOICES = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="questions"
    )
    question_text = models.TextField()
    option_a = models.CharField(max_length=300)
    option_b = models.CharField(max_length=300)
    option_c = models.CharField(max_length=300)
    option_d = models.CharField(max_length=300)
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES)
    marks = models.PositiveSmallIntegerField(default=1)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.question_text[:60]

    @property
    def options(self):
        """
        The four choices as (letter, text) pairs, so a template can loop them
        instead of repeating near-identical markup four times.

        Deliberately does NOT include correct_option -- nothing that renders
        this can leak the answer key into the page.
        """
        return [
            ("A", self.option_a),
            ("B", self.option_b),
            ("C", self.option_c),
            ("D", self.option_d),
        ]


class Attempt(models.Model):
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="attempts"
    )
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts"
    )
    score = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.learner.full_name} - {self.assessment.title} ({self.percentage}%)"


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    selected_option = models.CharField(max_length=1, blank=True)
    is_correct = models.BooleanField(default=False)


# ===========================================================================
# 6. CERTIFICATES
# ===========================================================================

class Certificate(models.Model):
    """
    Issued once, when a learner has finished all the material and passed the
    assessment.

    Two identifiers on purpose: the serial number is readable and sequential
    so it can be quoted, while the verification code is random so a forged
    certificate cannot be validated by guessing the next number in the series.
    """

    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.CASCADE, related_name="certificate"
    )
    serial_no = models.CharField(max_length=30, unique=True)
    verification_code = models.CharField(max_length=12, unique=True, db_index=True)
    issued_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_date"]

    def __str__(self):
        return self.serial_no


# ===========================================================================
# 7. FEEDBACK AND ANNOUNCEMENTS
# ===========================================================================

class Feedback(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="feedback")
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_given"
    )
    content_rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    # Feeds the trainer's competency score, so it is kept separate from the
    # rating of the course content itself.
    trainer_rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    overall_rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["course", "learner"], name="unique_feedback")
        ]


class AnnouncementType(models.TextChoices):
    NOTIFICATION = "NOTIFICATION", "Notification"
    ANNOUNCEMENT = "ANNOUNCEMENT", "Announcement"
    ACHIEVEMENT = "ACHIEVEMENT", "Achievement"
    NEW_CONTENT = "NEW_CONTENT", "New content"


class Announcement(models.Model):
    """
    Drives the public home page. One table covers all four kinds of notice the
    platform publishes; the type column says which.

    An announcement with no institution is platform-wide.
    """

    announcement_type = models.CharField(
        max_length=15, choices=AnnouncementType.choices, default=AnnouncementType.ANNOUNCEMENT
    )
    institution = models.ForeignKey(
        "accounts.Institution", on_delete=models.CASCADE, blank=True, null=True,
        related_name="announcements",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="announcements_posted",
    )
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-pinned", "-created_at"]

    def __str__(self):
        return self.title
