"""
Forms for courses, material, assessments and feedback.
"""

from django import forms
from django.conf import settings
from django.utils import timezone

from accounts.models import Role, User
from learning.models import (
    Assessment, Course, Feedback, Question, Resource, Subject,
)


def _style(fields, placeholders=None):
    placeholders = placeholders or {}
    for name, field in fields.items():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            css = "form-check-input"
        elif isinstance(widget, forms.Select):
            css = "form-select"
        else:
            css = "form-control"
        widget.attrs.setdefault("class", css)
        if name in placeholders:
            widget.attrs.setdefault("placeholder", placeholders[name])


class CourseForm(forms.ModelForm):
    """
    Used by an institute admin.

    The trainer dropdown is deliberately built from this institution's own
    trainers only. Without that filter, an admin could post another
    institution's trainer id and quietly attach their staff to a course.
    """

    class Meta:
        model = Course
        fields = ["code", "title", "subject", "trainer", "description",
                  "level", "duration_hours", "cover_image", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, institution=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {
            "code": "e.g. WD-101",
            "title": "e.g. Building Modern Web Applications",
        })
        self.fields["subject"].queryset = Subject.objects.all()
        self.fields["trainer"].queryset = User.objects.filter(
            role=Role.TRAINER, institution=institution, is_active=True
        )
        self.fields["trainer"].required = False
        self.fields["trainer"].empty_label = "Not assigned yet"
        self.fields["trainer"].help_text = "Only trainers from your institution appear here."


class ResourceForm(forms.ModelForm):
    """Used by a trainer to upload material."""

    class Meta:
        model = Resource
        fields = ["title", "description", "resource_type", "file", "link_url", "position"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {
            "title": "e.g. Week 1 - Recorded lecture",
            "link_url": "https://...",
        })
        self.fields["file"].required = False
        self.fields["link_url"].required = False
        self.fields["file"].help_text = (
            f"Video, PPT, PDF or document, up to {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("resource_type")
        uploaded = cleaned.get("file")
        link = cleaned.get("link_url")

        if kind == "LINK":
            if not link:
                self.add_error("link_url", "Give the address the link should point to.")
        elif not uploaded and not self.instance.pk:
            self.add_error("file", "Choose a file to upload.")

        if uploaded and uploaded.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            self.add_error(
                "file",
                f"That file is {uploaded.size / 1024 / 1024:.0f} MB. "
                f"The limit is {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )
        return cleaned


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ["title", "instructions", "deadline", "duration_minutes", "pass_percent"]
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 2}),
            "deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {"title": "e.g. Module 1 assessment"})
        self.fields["deadline"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["instructions"].required = False
        self.fields["pass_percent"].help_text = "Percentage needed to pass."

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]
        if deadline <= timezone.now():
            raise forms.ValidationError("The deadline needs to be in the future.")
        return deadline


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["question_text", "option_a", "option_b", "option_c", "option_d",
                  "correct_option", "marks"]
        widgets = {"question_text": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {
            "question_text": "Type the question",
            "option_a": "Option A",
            "option_b": "Option B",
            "option_c": "Option C",
            "option_d": "Option D",
        })
        self.fields["correct_option"].help_text = "Which option is right. Learners never see this."


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["content_rating", "trainer_rating", "overall_rating", "comments"]
        widgets = {"comments": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {"comments": "Anything you would tell the next learner?"})
        self.fields["comments"].required = False
        self.fields["trainer_rating"].help_text = (
            "This feeds the trainer's competency score."
        )
