"""
Every address on SkillScope, in one place.

Grouped by who uses it. The name in quotes at the end of each line is what
templates refer to, as in {% url 'course_catalog' %} -- so a URL can be changed
here without editing a single template.
"""

from django.conf import settings
from django.urls import re_path
from django.views.static import serve
from django.contrib import admin
from django.urls import path

from accounts import views as accounts_views
from competency import views as competency_views
from learning import views as learning_views

urlpatterns = [
    # ---------------------------------------------------------------- public
    path("", learning_views.home, name="home"),
    path("courses/", learning_views.course_catalog, name="course_catalog"),
    path("courses/<int:course_id>/", learning_views.course_detail, name="course_detail"),
    path("subjects/", learning_views.subject_list, name="subject_list"),
    path("institutions/", learning_views.institution_list, name="institution_list"),
    path("verify/", learning_views.verify_form, name="verify_form"),
    path("verify/<str:code>/", learning_views.verify_certificate, name="verify_certificate"),

    # ------------------------------------------------------------------ auth
    path("login/", accounts_views.login_view, name="login"),
    path("logout/", accounts_views.logout_view, name="logout"),
    path("register/", accounts_views.register_choice, name="register"),
    path("register/learner/", accounts_views.register_learner, name="register_learner"),
    path("register/institution/", accounts_views.register_institution, name="register_institution"),
    path("awaiting-verification/", accounts_views.awaiting_verification, name="awaiting_verification"),
    path("denied/", accounts_views.denied, name="denied"),

    # --------------------------------------------------------------- general
    path("dashboard/", accounts_views.dashboard, name="dashboard"),
    path("profile/", accounts_views.profile, name="profile"),
    path("profile/qualification/add/", accounts_views.add_qualification, name="add_qualification"),
    path("profile/experience/add/", accounts_views.add_experience, name="add_experience"),
    path("profile/skill/add/", accounts_views.add_skill, name="add_skill"),
    path("profile/certificate/add/", accounts_views.add_user_certificate, name="add_user_certificate"),
    path("profile/<str:kind>/<int:pk>/delete/", accounts_views.delete_profile_item, name="delete_profile_item"),

    # --------------------------------------------------------------- learner
    path("my-learning/", learning_views.my_learning, name="my_learning"),
    path("courses/<int:course_id>/enroll/", learning_views.enroll, name="enroll"),
    path("learn/<int:enrollment_id>/", learning_views.course_learn, name="course_learn"),
    path("learn/<int:enrollment_id>/complete/<int:resource_id>/",
         learning_views.mark_resource_done, name="mark_resource_done"),
    path("learn/<int:enrollment_id>/feedback/", learning_views.give_feedback, name="give_feedback"),
    path("assessment/<int:assessment_id>/take/", learning_views.assessment_take, name="assessment_take"),
    path("assessment/<int:assessment_id>/submit/", learning_views.assessment_submit, name="assessment_submit"),
    path("attempt/<int:attempt_id>/", learning_views.attempt_result, name="attempt_result"),
    path("certificates/", learning_views.my_certificates, name="my_certificates"),
    path("certificates/<int:certificate_id>/", learning_views.certificate_view, name="certificate_view"),

    # --------------------------------------------------------------- trainer
    path("trainer/courses/", learning_views.trainer_courses, name="trainer_courses"),
    path("trainer/courses/<int:course_id>/", learning_views.trainer_course_manage, name="trainer_course_manage"),
    path("trainer/courses/<int:course_id>/material/add/",
         learning_views.trainer_add_resource, name="trainer_add_resource"),
    path("trainer/resource/<int:resource_id>/delete/",
         learning_views.trainer_delete_resource, name="trainer_delete_resource"),
    path("trainer/library/", learning_views.trainer_library, name="trainer_library"),
    path("trainer/courses/<int:course_id>/assessment/new/",
         learning_views.trainer_create_assessment, name="trainer_create_assessment"),
    path("trainer/assessment/<int:assessment_id>/", learning_views.trainer_assessment_manage,
         name="trainer_assessment_manage"),
    path("trainer/assessment/<int:assessment_id>/question/add/",
         learning_views.trainer_add_question, name="trainer_add_question"),

    # ------------------------------------------------------- institute admin
    path("institute/courses/", learning_views.institute_courses, name="institute_courses"),
    path("institute/courses/new/", learning_views.institute_course_create, name="institute_course_create"),
    path("institute/courses/<int:course_id>/edit/", learning_views.institute_course_edit,
         name="institute_course_edit"),
    path("institute/trainers/", accounts_views.institute_trainers, name="institute_trainers"),
    path("institute/trainers/new/", accounts_views.institute_trainer_create, name="institute_trainer_create"),
    path("institute/learners/", learning_views.institute_learners, name="institute_learners"),
    path("institute/competency/", competency_views.institute_competency, name="institute_competency"),

    # -------------------------------------------------------- platform admin
    path("platform/institutions/", accounts_views.platform_institutions, name="platform_institutions"),
    path("platform/institutions/<int:institution_id>/",
         accounts_views.platform_institution_review, name="platform_institution_review"),
    path("platform/users/", accounts_views.platform_users, name="platform_users"),
    path("platform/announcements/", learning_views.platform_announcements, name="platform_announcements"),
    path("platform/competency/", competency_views.platform_competency, name="platform_competency"),
    path("platform/competency/subject/<int:subject_id>/",
         competency_views.subject_trainers, name="subject_trainers"),

    # Django's own admin, useful as a back door while building.
    path("django-admin/", admin.site.urls),
]

# During development Django serves uploaded files itself. A real deployment
# would put a web server in front of them instead.
# Serve our own CSS, JavaScript, fonts and uploaded files.
#
# django.conf.urls.static.static() cannot be used here: it returns nothing at
# all when DEBUG is off, because in a real deployment a separate web server
# does this job. SkillScope runs straight from a laptop, including in demo
# mode where DEBUG is deliberately off, so the URLs are wired to the serve
# view directly instead -- otherwise the whole site loads with no styling.
urlpatterns += [
    re_path(r"^static/(?P<path>.*)$", serve,
            {"document_root": settings.BASE_DIR / "static"}),
    re_path(r"^media/(?P<path>.*)$", serve,
            {"document_root": settings.MEDIA_ROOT}),
]
