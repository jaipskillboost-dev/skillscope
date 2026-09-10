"""
Forms for signing up, signing in, and editing a profile.

Django forms do three jobs at once: they draw the inputs, they check what came
back, and they turn it into a saved row. That is why there is no hand-written
validation in the views.
"""

from django import forms
from django.contrib.auth import authenticate

from accounts.models import Institution, Role, User
from learning.models import Experience, Qualification, Subject, UserCertificate, UserSkill


def _style(fields, placeholder_map=None):
    """Give every widget the Bootstrap class so the form looks right."""
    placeholder_map = placeholder_map or {}
    for name, field in fields.items():
        widget = field.widget
        css = "form-select" if isinstance(widget, forms.Select) else "form-control"
        if isinstance(widget, forms.CheckboxInput):
            css = "form-check-input"
        widget.attrs.setdefault("class", css)
        if name in placeholder_map:
            widget.attrs.setdefault("placeholder", placeholder_map[name])


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email address")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {"email": "you@example.com"})

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        password = cleaned.get("password")
        if email and password:
            user = authenticate(username=email.lower(), password=password)
            if user is None:
                raise forms.ValidationError("That email and password do not match an account.")
            if not user.is_active:
                raise forms.ValidationError("This account has been deactivated.")
            cleaned["user"] = user
        return cleaned


class LearnerRegisterForm(forms.ModelForm):
    """Anyone can sign up as a learner and start straight away."""

    password = forms.CharField(widget=forms.PasswordInput, min_length=8,
                               help_text="At least 8 characters.")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model = User
        fields = ["full_name", "email", "phone"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {"full_name": "Your name", "email": "you@example.com"})

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            self.add_error("confirm_password", "The two passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = Role.LEARNER
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class InstitutionApplicationForm(forms.ModelForm):
    """
    The institution half of the sign-up. Stays PENDING until a platform admin
    reviews the uploaded document.
    """

    class Meta:
        model = Institution
        fields = [
            "name", "institution_type", "registration_no", "description",
            "city", "state", "address",
            "contact_email", "contact_phone", "website",
            "logo", "document",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {
            "name": "e.g. Northline Institute of Technology",
            "registration_no": "Official registration number",
            "contact_email": "office@example.edu",
        })
        self.fields["document"].help_text = "Registration certificate or similar proof (PDF or image)."
        self.fields["state"].required = False
        self.fields["address"].required = False


class InstituteAdminRegisterForm(forms.ModelForm):
    """The person half of the institution sign-up."""

    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model = User
        fields = ["full_name", "email", "phone", "designation"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {"designation": "e.g. Training Head"})

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            self.add_error("confirm_password", "The two passwords do not match.")
        return cleaned


class TrainerCreateForm(forms.ModelForm):
    """
    Used by an institute admin to create a trainer account.

    Trainers do not sign themselves up -- the institution decides who teaches
    for it. The password is set here and shown once to the admin to pass on.
    """

    password = forms.CharField(widget=forms.PasswordInput, min_length=8,
                               help_text="Share this with the trainer. They can change it later.")

    class Meta:
        model = User
        fields = ["full_name", "email", "phone", "designation"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {"designation": "e.g. Senior Instructor"})

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "phone", "designation", "bio", "photo"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ["degree", "institution_name", "year_of_passing", "percentage"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {"degree": "e.g. B.Tech Computer Science"})
        self.fields["percentage"].required = False


class ExperienceForm(forms.ModelForm):
    """
    The subject is required, not optional.

    It is what links this row to the competency score. An experience with no
    subject is invisible to the trainer ranking, so the form insists on one.
    """

    class Meta:
        model = Experience
        fields = ["subject", "organisation", "designation", "from_year", "to_year",
                  "currently_working"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)
        self.fields["subject"].queryset = Subject.objects.all()
        self.fields["to_year"].required = False
        self.fields["subject"].help_text = "Which field this work counts towards."

    def clean(self):
        cleaned = super().clean()
        from_year = cleaned.get("from_year")
        to_year = cleaned.get("to_year")
        if from_year and to_year and to_year < from_year:
            self.add_error("to_year", "The end year cannot be before the start year.")
        if not cleaned.get("currently_working") and not to_year:
            self.add_error("to_year", "Give an end year, or tick 'currently working'.")
        return cleaned


class UserSkillForm(forms.ModelForm):
    class Meta:
        model = UserSkill
        fields = ["subject", "skill_name", "proficiency", "years_experience"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {"skill_name": "e.g. React, Kubernetes, Threat modelling"})
        self.fields["subject"].queryset = Subject.objects.all()


class UserCertificateForm(forms.ModelForm):
    class Meta:
        model = UserCertificate
        fields = ["title", "issuer", "issued_date", "file"]
        widgets = {"issued_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields, {"title": "e.g. AWS Solutions Architect"})


class InstitutionReviewForm(forms.Form):
    """What a platform admin fills in when rejecting an application."""

    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        required=False,
        help_text="Shown to the applicant. Required when rejecting.",
    )
