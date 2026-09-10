"""
Tests for the competency score.

Every expected number here was worked out by hand from the formula, so if
someone changes a weight these fail loudly rather than quietly producing a
different ranking.

    40%  average skill proficiency / 5
    30%  min(years in subject / 10, 1)
    30%  average trainer rating / 5      (3.0 when nobody has rated them)
"""

from django.test import TestCase
from django.utils import timezone

from accounts.models import Institution, InstitutionStatus, Role, User
from competency.services import (
    NEUTRAL_RATING, QUALIFIED_THRESHOLD, competency_gaps,
    rank_trainers_for_subject, score_trainer_for_subject,
)
from learning.models import (
    Course, CourseStatus, Enrollment, Experience, Feedback, Subject, UserSkill,
)


class CompetencyScoreTests(TestCase):
    def setUp(self):
        self.institution = Institution.objects.create(
            name="Test Institute", registration_no="TEST-1", city="Pune",
            contact_email="a@b.com", status=InstitutionStatus.VERIFIED,
        )
        self.subject = Subject.objects.create(code="TS", name="Test Subject")
        self.trainer = User.objects.create_user(
            email="t@test.com", password="x", full_name="Test Trainer",
            role=Role.TRAINER, institution=self.institution,
        )

    def _skill(self, proficiency):
        UserSkill.objects.create(user=self.trainer, subject=self.subject,
                                 skill_name="s", proficiency=proficiency)

    def _experience(self, years):
        Experience.objects.create(
            user=self.trainer, subject=self.subject, organisation="o",
            designation="d", from_year=timezone.now().year - years,
            currently_working=True,
        )

    def _rated_course(self, ratings):
        course = Course.objects.create(
            institution=self.institution, subject=self.subject, trainer=self.trainer,
            code=f"C{Course.objects.count()}", title="c", status=CourseStatus.PUBLISHED,
        )
        for i, rating in enumerate(ratings):
            learner = User.objects.create_user(
                email=f"l{i}{course.code}@test.com", password="x",
                full_name=f"Learner {i}", role=Role.LEARNER,
            )
            Enrollment.objects.create(course=course, learner=learner)
            Feedback.objects.create(course=course, learner=learner, content_rating=rating,
                                    trainer_rating=rating, overall_rating=rating)
        return course

    # ---------------------------------------------------------------- basics

    def test_empty_profile_scores_only_the_neutral_rating(self):
        """
        No skills, no experience, no ratings.

        Skill 0 + experience 0 + (3.0/5 * 30) = 18. Not zero, because an
        unrated trainer is treated as average rather than as terrible.
        """
        result = score_trainer_for_subject(self.trainer, self.subject)
        self.assertEqual(result["total"], 18)
        self.assertFalse(result["qualified"])

    def test_perfect_profile_scores_100(self):
        self._skill(5)
        self._experience(10)
        self._rated_course([5, 5, 5])
        result = score_trainer_for_subject(self.trainer, self.subject)
        self.assertEqual(result["total"], 100)
        self.assertTrue(result["qualified"])

    def test_each_factor_contributes_its_own_weight(self):
        self._skill(5)           # 40 * (5/5)  = 40
        self._experience(5)      # 30 * (5/10) = 15
        self._rated_course([4])  # 30 * (4/5)  = 24
        result = score_trainer_for_subject(self.trainer, self.subject)
        self.assertEqual(result["skill"]["points"], 40.0)
        self.assertEqual(result["experience"]["points"], 15.0)
        self.assertEqual(result["rating"]["points"], 24.0)
        self.assertEqual(result["total"], 79)

    # ------------------------------------------------------- the two rules

    def test_experience_is_capped_at_ten_years(self):
        """
        Thirty years should not beat ten. Without the cap, one very long
        career would swamp skill and rating together.
        """
        self._skill(3)
        self._experience(30)
        result = score_trainer_for_subject(self.trainer, self.subject)
        self.assertEqual(result["experience"]["points"], 30.0)
        self.assertEqual(result["experience"]["percent"], 100)

    def test_unrated_trainer_gets_the_neutral_rating_not_zero(self):
        self._skill(5)
        self._experience(10)
        result = score_trainer_for_subject(self.trainer, self.subject)
        expected = float(NEUTRAL_RATING) / 5 * 30
        self.assertEqual(result["rating"]["points"], round(expected, 1))
        self.assertEqual(result["rating"]["detail"], "not yet rated")
        # 40 + 30 + 18 = 88: a strong new trainer is still recommendable.
        self.assertEqual(result["total"], 88)

    def test_a_real_rating_replaces_the_neutral_one(self):
        self._rated_course([2, 2])
        result = score_trainer_for_subject(self.trainer, self.subject)
        self.assertEqual(result["rating"]["points"], 12.0)  # 30 * (2/5)
        self.assertIn("2 learners", result["rating"]["detail"])

    def test_score_only_counts_the_subject_asked_about(self):
        other = Subject.objects.create(code="OT", name="Other")
        UserSkill.objects.create(user=self.trainer, subject=other,
                                 skill_name="unrelated", proficiency=5)
        result = score_trainer_for_subject(self.trainer, self.subject)
        self.assertEqual(result["skill"]["points"], 0.0)

    # -------------------------------------------------------------- ranking

    def test_ranking_is_best_first(self):
        self._skill(5)
        self._experience(10)
        weaker = User.objects.create_user(
            email="w@test.com", password="x", full_name="Weaker",
            role=Role.TRAINER, institution=self.institution,
        )
        UserSkill.objects.create(user=weaker, subject=self.subject,
                                 skill_name="s", proficiency=1)
        ranked = rank_trainers_for_subject(self.subject)
        self.assertEqual(ranked[0]["trainer"], self.trainer)
        self.assertGreater(ranked[0]["total"], ranked[1]["total"])

    def test_ranking_can_be_narrowed_to_one_institution(self):
        """An institute admin must not see another institution's trainers."""
        other_institution = Institution.objects.create(
            name="Other", registration_no="TEST-2", city="Kochi",
            contact_email="c@d.com", status=InstitutionStatus.VERIFIED,
        )
        outsider = User.objects.create_user(
            email="out@test.com", password="x", full_name="Outsider",
            role=Role.TRAINER, institution=other_institution,
        )
        listed = [r["trainer"] for r in
                  rank_trainers_for_subject(self.subject, institution=self.institution)]
        self.assertIn(self.trainer, listed)
        self.assertNotIn(outsider, listed)

    # ---------------------------------------------------------- gap heatmap

    def test_subject_with_nobody_qualified_is_red(self):
        row = next(r for r in competency_gaps() if r["subject"] == self.subject)
        self.assertEqual(row["level"], "red")
        self.assertEqual(row["qualified_count"], 0)

    def test_subject_becomes_green_once_three_are_qualified(self):
        for i in range(3):
            trainer = User.objects.create_user(
                email=f"q{i}@test.com", password="x", full_name=f"Q{i}",
                role=Role.TRAINER, institution=self.institution,
            )
            UserSkill.objects.create(user=trainer, subject=self.subject,
                                     skill_name="s", proficiency=5)
            Experience.objects.create(
                user=trainer, subject=self.subject, organisation="o", designation="d",
                from_year=timezone.now().year - 10, currently_working=True,
            )
        row = next(r for r in competency_gaps() if r["subject"] == self.subject)
        self.assertEqual(row["qualified_count"], 3)
        self.assertEqual(row["level"], "green")

    def test_threshold_boundary_counts_as_qualified(self):
        """Exactly the threshold is qualified, not one short of it."""
        self._skill(3)           # 40 * 3/5  = 24
        self._experience(6)      # 30 * 6/10 = 18
        self._rated_course([3])  # 30 * 3/5  = 18   -> 60 exactly
        result = score_trainer_for_subject(self.trainer, self.subject)
        self.assertEqual(result["total"], QUALIFIED_THRESHOLD)
        self.assertTrue(result["qualified"])
