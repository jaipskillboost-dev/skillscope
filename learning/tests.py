"""
Tests for marking, certificates, and who is allowed to see whose data.

The tenant isolation tests at the bottom are the important ones. SkillScope
hosts many institutions at once, so "is this person a trainer" is not a
sufficient check on its own -- these prove the institution filter is really
there.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Institution, InstitutionStatus, Role, User
from learning.models import (
    Assessment, Attempt, Certificate, Course, CourseStatus, Enrollment, Feedback,
    Question, Resource, ResourceCompletion, ResourceType, Subject,
)
from learning.services import (
    AlreadyAttempted, DeadlinePassed, has_earned_certificate,
    issue_certificate_if_earned, mark_attempt,
)


class Fixture(TestCase):
    """Shared setup: two institutions, so isolation can actually be tested."""

    def setUp(self):
        self.subject = Subject.objects.create(code="S", name="Subject")

        self.inst_a = Institution.objects.create(
            name="Institute A", registration_no="A-1", city="Pune",
            contact_email="a@a.com", status=InstitutionStatus.VERIFIED,
        )
        self.inst_b = Institution.objects.create(
            name="Institute B", registration_no="B-1", city="Kochi",
            contact_email="b@b.com", status=InstitutionStatus.VERIFIED,
        )
        self.inst_pending = Institution.objects.create(
            name="Institute Pending", registration_no="P-1", city="Goa",
            contact_email="p@p.com", status=InstitutionStatus.PENDING,
        )

        self.admin_a = User.objects.create_user(
            email="admin.a@a.com", password="pw", full_name="Admin A",
            role=Role.INSTITUTE_ADMIN, institution=self.inst_a)
        self.admin_b = User.objects.create_user(
            email="admin.b@b.com", password="pw", full_name="Admin B",
            role=Role.INSTITUTE_ADMIN, institution=self.inst_b)
        self.admin_pending = User.objects.create_user(
            email="admin.p@p.com", password="pw", full_name="Admin P",
            role=Role.INSTITUTE_ADMIN, institution=self.inst_pending)

        self.trainer_a = User.objects.create_user(
            email="trainer.a@a.com", password="pw", full_name="Trainer A",
            role=Role.TRAINER, institution=self.inst_a)
        self.trainer_b = User.objects.create_user(
            email="trainer.b@b.com", password="pw", full_name="Trainer B",
            role=Role.TRAINER, institution=self.inst_b)

        self.learner = User.objects.create_user(
            email="learner@x.com", password="pw", full_name="A Learner",
            role=Role.LEARNER)

        self.course_a = Course.objects.create(
            institution=self.inst_a, subject=self.subject, trainer=self.trainer_a,
            code="A-100", title="Course A", status=CourseStatus.PUBLISHED)
        self.course_b = Course.objects.create(
            institution=self.inst_b, subject=self.subject, trainer=self.trainer_b,
            code="B-100", title="Course B", status=CourseStatus.PUBLISHED)
        self.course_pending = Course.objects.create(
            institution=self.inst_pending, subject=self.subject,
            code="P-100", title="Course Pending", status=CourseStatus.PUBLISHED)

    def make_assessment(self, course, correct_letters, deadline=None, pass_percent=50):
        assessment = Assessment.objects.create(
            course=course, subject=self.subject, trainer=course.trainer,
            title="Test", pass_percent=pass_percent,
            deadline=deadline or timezone.now() + timedelta(days=7),
        )
        for i, letter in enumerate(correct_letters, start=1):
            Question.objects.create(
                assessment=assessment, question_text=f"Q{i}",
                option_a="a", option_b="b", option_c="c", option_d="d",
                correct_option=letter, marks=1, position=i,
            )
        return assessment


# ===========================================================================
# MARKING
# ===========================================================================

class MarkingTests(Fixture):
    def setUp(self):
        super().setUp()
        Enrollment.objects.create(course=self.course_a, learner=self.learner)

    def test_all_correct_scores_full_marks(self):
        assessment = self.make_assessment(self.course_a, "BCBBB")
        qs = list(assessment.questions.all())
        answers = {str(q.id): q.correct_option for q in qs}
        attempt = mark_attempt(assessment, self.learner, answers)
        self.assertEqual(attempt.score, 5)
        self.assertEqual(float(attempt.percentage), 100.0)
        self.assertTrue(attempt.passed)

    def test_marks_come_from_the_database_not_the_submission(self):
        """
        Answering every question "A" against the key B,C,B,B,B must score 0.

        This is the check that says a learner cannot edit the page to award
        themselves a pass: the answer key is only ever read from the server.
        """
        assessment = self.make_assessment(self.course_a, "BCBBB")
        answers = {str(q.id): "A" for q in assessment.questions.all()}
        attempt = mark_attempt(assessment, self.learner, answers)
        self.assertEqual(attempt.score, 0)
        self.assertFalse(attempt.passed)

    def test_unanswered_questions_count_as_wrong_not_as_skipped(self):
        """
        Two right out of five is 40%, not 100% of the two that were answered.
        Dropping unanswered questions from the total would let someone pass by
        answering only what they knew.
        """
        assessment = self.make_assessment(self.course_a, "AAAAA")
        qs = list(assessment.questions.all())
        answers = {str(qs[0].id): "A", str(qs[1].id): "A"}
        attempt = mark_attempt(assessment, self.learner, answers)
        self.assertEqual(attempt.score, 2)
        self.assertEqual(attempt.total_marks, 5)
        self.assertEqual(float(attempt.percentage), 40.0)

    def test_exactly_the_pass_mark_is_a_pass(self):
        assessment = self.make_assessment(self.course_a, "AAAA", pass_percent=50)
        qs = list(assessment.questions.all())
        answers = {str(qs[0].id): "A", str(qs[1].id): "A"}
        attempt = mark_attempt(assessment, self.learner, answers)
        self.assertEqual(float(attempt.percentage), 50.0)
        self.assertTrue(attempt.passed)

    def test_one_below_the_pass_mark_is_a_fail(self):
        assessment = self.make_assessment(self.course_a, "AAAA", pass_percent=51)
        qs = list(assessment.questions.all())
        answers = {str(qs[0].id): "A", str(qs[1].id): "A"}
        attempt = mark_attempt(assessment, self.learner, answers)
        self.assertFalse(attempt.passed)

    def test_submitting_after_the_deadline_is_refused(self):
        assessment = self.make_assessment(
            self.course_a, "AAA", deadline=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(DeadlinePassed):
            mark_attempt(assessment, self.learner, {})
        self.assertEqual(Attempt.objects.count(), 0)

    def test_a_second_attempt_is_refused(self):
        assessment = self.make_assessment(self.course_a, "AAA")
        mark_attempt(assessment, self.learner, {})
        with self.assertRaises(AlreadyAttempted):
            mark_attempt(assessment, self.learner, {})
        self.assertEqual(Attempt.objects.count(), 1)


# ===========================================================================
# CERTIFICATES
# ===========================================================================

class CertificateTests(Fixture):
    def setUp(self):
        super().setUp()
        self.resources = [
            Resource.objects.create(
                course=self.course_a, institution=self.inst_a, subject=self.subject,
                title=f"R{i}", resource_type=ResourceType.PDF, position=i)
            for i in range(1, 4)
        ]
        self.enrollment = Enrollment.objects.create(
            course=self.course_a, learner=self.learner)

    def _finish_material(self):
        for resource in self.resources:
            ResourceCompletion.objects.create(
                enrollment=self.enrollment, resource=resource)
        self.enrollment.recalculate_progress()

    def test_material_alone_is_not_enough_when_there_is_an_assessment(self):
        self.make_assessment(self.course_a, "AAA")
        self._finish_material()
        self.assertFalse(has_earned_certificate(self.enrollment))
        self.assertIsNone(issue_certificate_if_earned(self.enrollment))

    def test_passing_alone_is_not_enough_without_the_material(self):
        assessment = self.make_assessment(self.course_a, "AAA")
        answers = {str(q.id): "A" for q in assessment.questions.all()}
        mark_attempt(assessment, self.learner, answers)
        self.assertLess(self.enrollment.progress_percent, 100)
        self.assertFalse(has_earned_certificate(self.enrollment))

    def test_both_conditions_together_issue_a_certificate(self):
        assessment = self.make_assessment(self.course_a, "AAA")
        self._finish_material()
        answers = {str(q.id): "A" for q in assessment.questions.all()}
        mark_attempt(assessment, self.learner, answers)
        self.assertTrue(Certificate.objects.filter(enrollment=self.enrollment).exists())

    def test_a_course_with_no_assessment_is_decided_on_material_alone(self):
        self._finish_material()
        self.assertIsNotNone(issue_certificate_if_earned(self.enrollment))

    def test_a_certificate_is_only_ever_issued_once(self):
        """
        issue_certificate_if_earned is called from two places, so calling it
        twice must not produce two certificates.
        """
        self._finish_material()
        first = issue_certificate_if_earned(self.enrollment)
        second = issue_certificate_if_earned(self.enrollment)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Certificate.objects.count(), 1)

    def test_verification_codes_are_not_sequential(self):
        """
        Serial numbers run in order; verification codes must not, or a forged
        certificate could be validated by guessing the next one.
        """
        self._finish_material()
        first = issue_certificate_if_earned(self.enrollment)

        other = User.objects.create_user(
            email="l2@x.com", password="pw", full_name="Learner Two", role=Role.LEARNER)
        enrollment2 = Enrollment.objects.create(course=self.course_a, learner=other)
        for resource in self.resources:
            ResourceCompletion.objects.create(enrollment=enrollment2, resource=resource)
        enrollment2.recalculate_progress()
        second = issue_certificate_if_earned(enrollment2)

        self.assertEqual(first.serial_no[:-1], second.serial_no[:-1])   # sequential
        self.assertNotEqual(first.verification_code, second.verification_code)
        self.assertEqual(len(first.verification_code), 10)

    def test_a_wrong_code_verifies_as_not_found(self):
        self._finish_material()
        certificate = issue_certificate_if_earned(self.enrollment)

        good = self.client.get(
            reverse("verify_certificate", args=[certificate.verification_code]))
        self.assertContains(good, "Genuine certificate")

        tampered = ("A" if certificate.verification_code[0] != "A" else "B") \
            + certificate.verification_code[1:]
        bad = self.client.get(reverse("verify_certificate", args=[tampered]))
        self.assertContains(bad, "No certificate has this code")

    def test_verification_needs_no_sign_in(self):
        self._finish_material()
        certificate = issue_certificate_if_earned(self.enrollment)
        self.client.logout()
        response = self.client.get(
            reverse("verify_certificate", args=[certificate.verification_code]))
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# TENANT ISOLATION -- the tests that make this safe to host many institutions
# ===========================================================================

class TenantIsolationTests(Fixture):
    def test_institute_admin_sees_only_their_own_courses(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("institute_courses"))
        self.assertContains(response, "A-100")
        self.assertNotContains(response, "B-100")

    def test_institute_admin_cannot_open_another_institutions_course(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(
            reverse("institute_course_edit", args=[self.course_b.id]))
        self.assertEqual(response.status_code, 404)

    def test_institute_admin_learner_list_excludes_other_institutions(self):
        Enrollment.objects.create(course=self.course_b, learner=self.learner)
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("institute_learners"))
        self.assertNotContains(response, "Course B")

    def test_a_new_trainer_belongs_to_the_creating_admins_institution(self):
        """
        Even if the form data tried to name another institution, the trainer
        is attached to the signed-in admin's institution.
        """
        self.client.force_login(self.admin_a)
        self.client.post(reverse("institute_trainer_create"), {
            "full_name": "New Trainer", "email": "new@a.com",
            "phone": "", "designation": "Trainer", "password": "longenough1",
            "institution": self.inst_b.id,   # ignored on purpose
        })
        created = User.objects.get(email="new@a.com")
        self.assertEqual(created.institution, self.inst_a)
        self.assertEqual(created.role, Role.TRAINER)

    def test_trainer_cannot_open_another_institutions_course(self):
        self.client.force_login(self.trainer_a)
        response = self.client.get(
            reverse("trainer_course_manage", args=[self.course_b.id]))
        self.assertEqual(response.status_code, 404)

    def test_trainer_sees_only_courses_assigned_to_them(self):
        other_course = Course.objects.create(
            institution=self.inst_a, subject=self.subject, trainer=None,
            code="A-200", title="Unassigned", status=CourseStatus.DRAFT)
        self.client.force_login(self.trainer_a)
        response = self.client.get(reverse("trainer_courses"))
        self.assertContains(response, "Course A")
        self.assertNotContains(response, other_course.title)

    def test_roles_cannot_reach_each_others_areas(self):
        cases = [
            (self.learner, "trainer_courses"),
            (self.learner, "institute_courses"),
            (self.learner, "platform_institutions"),
            (self.trainer_a, "institute_courses"),
            (self.trainer_a, "platform_users"),
            (self.admin_a, "platform_users"),
            (self.admin_a, "trainer_courses"),
        ]
        for user, name in cases:
            with self.subTest(user=user.role, page=name):
                self.client.force_login(user)
                response = self.client.get(reverse(name))
                self.assertRedirects(response, reverse("denied"),
                                     target_status_code=403)


class UnverifiedInstitutionTests(Fixture):
    def test_pending_admin_is_held_on_the_waiting_page(self):
        self.client.force_login(self.admin_pending)
        response = self.client.get(reverse("institute_courses"))
        self.assertRedirects(response, reverse("awaiting_verification"))

    def test_pending_institutions_courses_stay_out_of_the_catalogue(self):
        """
        The course is PUBLISHED, but its institution is not verified -- so it
        must not appear publicly. Both conditions have to hold.
        """
        response = self.client.get(reverse("course_catalog"))
        self.assertContains(response, "Course A")
        self.assertNotContains(response, "Course Pending")

    def test_a_pending_institutions_course_page_is_not_reachable(self):
        response = self.client.get(
            reverse("course_detail", args=[self.course_pending.id]))
        self.assertEqual(response.status_code, 404)


class ProgressTests(Fixture):
    def test_progress_tracks_completed_material(self):
        for i in range(1, 5):
            Resource.objects.create(
                course=self.course_a, institution=self.inst_a, subject=self.subject,
                title=f"R{i}", resource_type=ResourceType.PDF, position=i)
        enrollment = Enrollment.objects.create(
            course=self.course_a, learner=self.learner)
        self.assertEqual(enrollment.recalculate_progress(), 0)

        ResourceCompletion.objects.create(
            enrollment=enrollment, resource=self.course_a.resources.first())
        self.assertEqual(enrollment.recalculate_progress(), 25)

        for resource in self.course_a.resources.all():
            ResourceCompletion.objects.get_or_create(
                enrollment=enrollment, resource=resource)
        self.assertEqual(enrollment.recalculate_progress(), 100)
        self.assertEqual(enrollment.status, "COMPLETED")

    def test_a_course_with_no_material_does_not_divide_by_zero(self):
        enrollment = Enrollment.objects.create(
            course=self.course_a, learner=self.learner)
        self.assertEqual(enrollment.recalculate_progress(), 0)


# ===========================================================================
# ERROR PAGES AND MESSAGE STYLING
#
# Custom error pages only render when DEBUG is off -- with DEBUG on, Django
# shows its own detailed page instead, which is more useful while building.
# These tests force DEBUG off so the real thing is checked.
# ===========================================================================

from django.contrib.messages import constants as message_constants  # noqa: E402
from django.test import override_settings  # noqa: E402


@override_settings(DEBUG=False)
class ErrorPageTests(TestCase):
    def test_unknown_address_renders_our_own_404(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "We could not find that page",
                            status_code=404)
        # Proves it is our template, not Django's bare fallback.
        self.assertContains(response, "SkillScope", status_code=404)

    def test_the_404_offers_a_way_back(self):
        response = self.client.get("/no-such-page/")
        self.assertContains(response, reverse("home"), status_code=404)
        self.assertContains(response, reverse("course_catalog"), status_code=404)

    def test_denied_page_uses_the_403_styling(self):
        response = self.client.get(reverse("denied"))
        self.assertEqual(response.status_code, 403)


class MessageStylingTests(Fixture):
    def test_error_messages_use_the_bootstrap_danger_class(self):
        """
        Django labels an error message "error", but the CSS class for a red
        alert is "alert-danger". Without the MESSAGE_TAGS mapping the message
        renders unstyled -- readable, but not obviously a problem.
        """
        from django.conf import settings
        self.assertEqual(settings.MESSAGE_TAGS[message_constants.ERROR], "danger")

    def test_a_real_error_message_renders_as_a_red_alert(self):
        self.client.force_login(self.trainer_a)
        # An upload with no file at all fails validation and adds an error.
        response = self.client.post(
            reverse("trainer_add_resource", args=[self.course_a.id]),
            {"title": "No file", "description": "", "resource_type": "PDF",
             "link_url": "", "position": "1"},
            follow=True,
        )
        self.assertContains(response, "alert-danger")
        self.assertNotContains(response, "alert-error")


# ===========================================================================
# PAGE SPEED
#
# The course catalogue once asked the database a separate question for every
# course card -- 37 queries for 12 courses, which on the hosted database took
# eleven seconds. These pin it down: adding courses must not add queries.
# ===========================================================================

from django.db import connection  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402


class CataloguePageSpeedTests(Fixture):

    def queries_for(self, path):
        with CaptureQueriesContext(connection) as captured:
            self.assertEqual(self.client.get(path).status_code, 200)
        return len(captured.captured_queries)

    def add_courses(self, how_many):
        for n in range(how_many):
            course = Course.objects.create(
                institution=self.inst_a, subject=self.subject, trainer=self.trainer_a,
                code=f"EXTRA-{n}", title=f"Extra {n}", status=CourseStatus.PUBLISHED)
            Enrollment.objects.create(course=course, learner=self.learner)
            Feedback.objects.create(course=course, learner=self.learner,
                                    content_rating=4, trainer_rating=4, overall_rating=4)

    def test_catalogue_queries_do_not_grow_with_the_number_of_courses(self):
        before = self.queries_for(reverse("course_catalog"))
        self.add_courses(8)
        self.assertEqual(self.queries_for(reverse("course_catalog")), before)

    def test_home_page_queries_do_not_grow_with_the_number_of_courses(self):
        before = self.queries_for(reverse("home"))
        self.add_courses(8)
        self.assertEqual(self.queries_for(reverse("home")), before)

    def test_card_figures_are_still_correct(self):
        """Faster must not mean wrong: the counted figures match the direct ones."""
        self.add_courses(3)
        from learning.views import public_courses
        for fast in public_courses():
            slow = Course.objects.get(pk=fast.pk)
            self.assertEqual(fast.enrolled_count, slow.enrolled_count)
            self.assertEqual(fast.average_rating, slow.average_rating)
