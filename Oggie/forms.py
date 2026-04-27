from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    AdoptionApplication,
    Announcement,
    Cat,
    CatIncident,
    Donation,
    FeedingSite,
    Foundation,
    Profile,
)


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True, label='First name')
    last_name = forms.CharField(max_length=150, required=False, label='Last name (optional)')
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class AccountSettingsForm(forms.ModelForm):
    """Lets a logged-in user edit their own name and email.

    Foundation membership is granted by foundation admins — not self-service —
    so it is not editable here.
    """

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        labels = {'last_name': 'Last name (optional)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['last_name'].required = False


class FoundationMemberAddForm(forms.Form):
    """Admin form to grant one or more existing users access to their foundation."""
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'searchable-multi', 'size': 8}),
        label='Select users to add',
        help_text='Start typing to filter by username, name, or email.',
    )
    make_admin = forms.BooleanField(
        required=False,
        label='Also promote them to admin',
        help_text='Admins can manage this foundation\'s member list too.',
    )

    def __init__(self, *args, foundation=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(is_active=True)
        if foundation is not None:
            qs = qs.exclude(profile__foundations=foundation)
        qs = qs.order_by('first_name', 'username')
        self.fields['users'].queryset = qs
        self.fields['users'].label_from_instance = (
            lambda u: f'{u.get_full_name() or u.username}'
                      f' — @{u.username}'
                      f'{(" · " + u.email) if u.email else ""}'
        )


class AdoptionApplicationForm(forms.ModelForm):
    class Meta:
        model = AdoptionApplication
        fields = ('message', 'living_situation')
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
            'living_situation': forms.Textarea(attrs={'rows': 4}),
        }


class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ('foundation', 'amount', 'name', 'email', 'message', 'is_anonymous')
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Leave a kind note (optional)'}),
        }
        labels = {
            'amount': 'Amount (PHP)',
            'is_anonymous': 'Make this donation anonymous',
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= 0:
            raise forms.ValidationError('Donation amount must be greater than zero.')
        return amount


CAT_PROFILE_FIELDS = (
    'name', 'description', 'birthday', 'age_years', 'gender',
    'photo', 'status', 'is_neutered', 'is_vaccinated',
    'feeding_sites', 'parents',
)


class CatForm(forms.ModelForm):
    class Meta:
        model = Cat
        fields = CAT_PROFILE_FIELDS
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'feeding_sites': forms.CheckboxSelectMultiple,
            'parents': forms.SelectMultiple(attrs={'class': 'searchable-multi', 'size': 6}),
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, foundation=None, **kwargs):
        super().__init__(*args, **kwargs)
        if foundation is not None:
            self.fields['feeding_sites'].queryset = FeedingSite.objects.filter(foundation=foundation)
        # Exclude self from parents list when editing
        if self.instance and self.instance.pk:
            self.fields['parents'].queryset = Cat.objects.exclude(pk=self.instance.pk)


class ApplicationReviewForm(forms.Form):
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.HiddenInput)


class CatIncidentForm(forms.ModelForm):
    class Meta:
        model = CatIncident
        fields = ('incident_type', 'description', 'photo', 'reporter_name', 'reporter_email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the empty "-------" option that Django adds by default for required
        # ChoiceField — the card-button UI makes the empty option meaningless.
        self.fields['incident_type'].choices = CatIncident.TYPE_CHOICES
        widgets = {
            # incident_type rendered as card-radio buttons in the template —
            # the plain select is hidden and JS syncs the selection.
            'incident_type': forms.HiddenInput(),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'e.g. "Found limping near the east gate — right front paw is hurt. I left a small amount of food nearby."',
            }),
            'reporter_name': forms.TextInput(attrs={'placeholder': 'Your name (optional)'}),
            'reporter_email': forms.EmailInput(attrs={'placeholder': 'Email for follow-up (optional)'}),
        }
        labels = {
            'reporter_name': 'Your name',
            'reporter_email': 'Your email',
        }


class FoundationIncidentReviewForm(forms.ModelForm):
    class Meta:
        model = CatIncident
        fields = ('status', 'foundation_notes')
        widgets = {'foundation_notes': forms.Textarea(attrs={'rows': 3})}


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ('title', 'body', 'is_active')
        widgets = {'body': forms.Textarea(attrs={'rows': 4})}


class FeedingSiteForm(forms.ModelForm):
    class Meta:
        model = FeedingSite
        fields = (
            'name', 'latitude', 'longitude', 'schedule',
            'point_persons', 'contact_details', 'notes',
        )
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'point_persons': forms.SelectMultiple(attrs={'class': 'searchable-multi', 'size': 6}),
            'contact_details': forms.TextInput(attrs={'placeholder': 'e.g. 0917-000-0000 or coordinator@example.com'}),
        }

    def __init__(self, *args, foundation=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Point persons are picked from this foundation's own members — the
        # roster managed by its admins on /foundation/members/.
        if foundation is not None:
            qs = User.objects.filter(profile__foundations=foundation)
        else:
            qs = User.objects.none()
        self.fields['point_persons'].queryset = qs.order_by('first_name', 'username')
        self.fields['point_persons'].label_from_instance = (
            lambda u: u.get_full_name() or u.username
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('latitude') is None or cleaned.get('longitude') is None:
            raise forms.ValidationError('Please click the map to set a location.')
        return cleaned


class CatReportForm(forms.ModelForm):
    class Meta:
        model = Cat
        fields = (
            'name', 'description', 'birthday', 'age_years', 'gender', 'photo',
            'is_neutered', 'is_vaccinated',
            'found_lat', 'found_lng', 'found_address',
            'feeding_sites',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Color, size, behavior, injuries, etc.'}),
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'found_lat': forms.HiddenInput(),
            'found_lng': forms.HiddenInput(),
            'found_address': forms.TextInput(attrs={'placeholder': 'e.g. "Near the market, Brgy. San Pedro"'}),
            'feeding_sites': forms.SelectMultiple(attrs={'class': 'searchable-multi', 'size': 6}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('found_lat') is None or cleaned.get('found_lng') is None:
            raise forms.ValidationError('Please click the map to set where you spotted the cat.')
        return cleaned


# ── Staff admin forms ──────────────────────────────────────────────────────


class StaffFoundationForm(forms.ModelForm):
    class Meta:
        model = Foundation
        fields = ('name', 'description', 'contact_email', 'phone', 'logo')
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class StaffUserCreateForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True, label='First name')
    last_name = forms.CharField(max_length=150, required=False, label='Last name (optional)')
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, initial=Profile.ROLE_ADOPTER)
    foundations = forms.ModelMultipleChoiceField(
        queryset=Foundation.objects.all(), required=False,
        widget=forms.SelectMultiple(attrs={'class': 'searchable-multi', 'size': 6}),
    )
    is_staff = forms.BooleanField(required=False, label='Also grant Oggie staff access')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def clean(self):
        cleaned = super().clean()
        # If is_staff is on, force role=staff for clarity.
        if cleaned.get('is_staff'):
            cleaned['role'] = Profile.ROLE_STAFF
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data['email']
        user.is_staff = self.cleaned_data.get('is_staff', False)
        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data['role']
            profile.save()
            profile.foundations.set(self.cleaned_data.get('foundations') or [])
        return user


class StaffUserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES)
    foundations = forms.ModelMultipleChoiceField(
        queryset=Foundation.objects.all(), required=False,
        widget=forms.SelectMultiple(attrs={'class': 'searchable-multi', 'size': 6}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
        labels = {'last_name': 'Last name (optional)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['last_name'].required = False
        if self.instance and self.instance.pk:
            profile = getattr(self.instance, 'profile', None)
            if profile:
                self.fields['role'].initial = profile.role
                self.fields['foundations'].initial = list(
                    profile.foundations.values_list('pk', flat=True)
                )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('is_staff'):
            cleaned['role'] = Profile.ROLE_STAFF
        elif cleaned.get('role') == Profile.ROLE_STAFF and not cleaned.get('is_staff'):
            # Staff role without is_staff doesn't make sense — downgrade.
            cleaned['role'] = Profile.ROLE_ADOPTER
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = user.profile
            profile.role = self.cleaned_data['role']
            profile.save()
            profile.foundations.set(self.cleaned_data.get('foundations') or [])
        return user


class StaffCatForm(forms.ModelForm):
    class Meta:
        model = Cat
        fields = (
            'name', 'description', 'birthday', 'age_years', 'gender', 'photo',
            'status', 'foundation', 'is_neutered', 'is_vaccinated',
            'feeding_sites', 'parents',
            'found_lat', 'found_lng', 'found_address',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'feeding_sites': forms.SelectMultiple(attrs={'class': 'searchable-multi', 'size': 6}),
            'parents': forms.SelectMultiple(attrs={'class': 'searchable-multi', 'size': 6}),
            'found_lat': forms.HiddenInput(),
            'found_lng': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['parents'].queryset = Cat.objects.exclude(pk=self.instance.pk)


class CatMergeForm(forms.Form):
    """Pick an existing cat to merge *this* cat into, then delete this one."""
    target = forms.ModelChoiceField(
        queryset=Cat.objects.none(),
        label='Merge into which existing cat?',
        help_text=(
            "By default the source's data fills in any blanks on the target. "
            'Tick "Prefer source fields" to overwrite target fields instead.'
        ),
    )
    prefer_source = forms.BooleanField(
        required=False,
        label='Prefer source fields',
        help_text=(
            'When checked, the source cat\'s photo, description, and location '
            'overwrite the target\'s — use this if the source report is fresher.'
        ),
    )

    def __init__(self, *args, source=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Cat.objects.exclude(pk=source.pk) if source else Cat.objects.all()
        self.fields['target'].queryset = qs.order_by('name')
        self.fields['target'].label_from_instance = (
            lambda c: f'{c.name} — {c.foundation.name if c.foundation else "unclaimed"}'
        )
