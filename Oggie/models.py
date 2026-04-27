from datetime import date

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Foundation(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    contact_email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    logo = models.ImageField(upload_to='foundations/', blank=True, null=True)
    # `admins` is the subset of `members` (Profile.foundations reverse M2M) who
    # can manage the member list. Everyone in admins is expected to also be a
    # member; the FoundationAdminRequiredMixin gates management views on this.
    admins = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='foundations_as_admin',
        help_text='Admins can add/remove members and promote other members to admin. '
                  'All admins must also be members of this foundation.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('foundation_detail', kwargs={'pk': self.pk})


class Profile(models.Model):
    ROLE_ADOPTER = 'adopter'
    ROLE_FOUNDATION = 'foundation'
    ROLE_STAFF = 'staff'
    ROLE_CHOICES = [
        (ROLE_ADOPTER, 'Adopter/Donor'),
        (ROLE_FOUNDATION, 'Foundation Partner'),
        (ROLE_STAFF, 'Oggie Staff'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_ADOPTER)
    foundations = models.ManyToManyField(
        Foundation,
        blank=True,
        related_name='members',
        help_text='Foundations this user belongs to. A user can belong to multiple foundations.',
    )
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'

    @property
    def is_foundation(self):
        return self.role == self.ROLE_FOUNDATION and self.foundations.exists()

    @property
    def is_oggie_staff(self):
        return self.user.is_staff

    def primary_foundation(self):
        """The user's default foundation when one must be chosen."""
        return self.foundations.first()

    def is_admin_of(self, foundation):
        """True if this user is an admin (not just member) of `foundation`.

        Oggie staff always pass. Returning False for anonymous / unset args
        keeps templates safe to call even with half-populated context.
        """
        if foundation is None:
            return False
        if self.user.is_staff:
            return True
        return foundation.admins.filter(pk=self.user.pk).exists()


class FeedingSite(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    schedule = models.CharField(max_length=200, help_text='e.g. "Daily 6pm" or "Mon/Wed/Fri 7am"')
    point_persons = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='feeding_sites_managed',
        help_text='Staff members coordinating this site. Pick one or more.',
    )
    contact_details = models.CharField(
        max_length=200, blank=True,
        help_text='Phone, email, or anything else volunteers should use to reach the point person(s).',
    )
    foundation = models.ForeignKey(
        Foundation,
        on_delete=models.CASCADE,
        related_name='feeding_sites',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def point_persons_display(self):
        names = [u.get_full_name() or u.username for u in self.point_persons.all()]
        return ', '.join(names) if names else '—'


class Cat(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('U', 'Unknown'),
    ]
    STATUS_STRAY = 'stray'
    STATUS_IN_CARE = 'in_care'
    STATUS_AVAILABLE = 'available'
    STATUS_ADOPTED = 'adopted'
    STATUS_CHOICES = [
        (STATUS_STRAY, 'Stray (spotted)'),
        (STATUS_IN_CARE, 'In Care'),
        (STATUS_AVAILABLE, 'Available for Adoption'),
        (STATUS_ADOPTED, 'Adopted'),
    ]

    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    description = models.TextField(
        blank=True,
        help_text='Highly encouraged — color, markings, temperament, medical notes, etc.',
    )
    birthday = models.DateField(
        null=True, blank=True,
        help_text='Exact birthday if known. If left blank, use "estimated age" below.',
    )
    age_years = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Estimated age in years — used only if birthday is unknown.',
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    photo = models.ImageField(upload_to='cats/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_STRAY)
    is_neutered = models.BooleanField(default=False)
    is_vaccinated = models.BooleanField(default=False)
    foundation = models.ForeignKey(
        Foundation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cats',
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reported_cats',
    )
    found_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    found_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    found_address = models.CharField(max_length=200, blank=True)
    feeding_sites = models.ManyToManyField(FeedingSite, blank=True, related_name='cats')
    parents = models.ManyToManyField(
        'self', symmetrical=False, blank=True, related_name='children',
        help_text='Known parents of this cat (adds this cat as their child automatically).',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or 'cat'
            slug = base
            i = 2
            while Cat.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('cat_detail', kwargs={'slug': self.slug})

    # Default stand-in when no photo was uploaded. Rendered in place of <img>.
    PLACEHOLDER_EMOJI = '😼'

    @property
    def has_photo(self):
        return bool(self.photo)

    @property
    def is_verified(self):
        """Community-reported cat that has been claimed by a foundation."""
        return self.reported_by_id is not None and self.foundation_id is not None

    @property
    def age_display(self):
        """Best-available age string: computed from birthday if set, else estimated years."""
        if self.birthday:
            today = date.today()
            years = today.year - self.birthday.year - (
                (today.month, today.day) < (self.birthday.month, self.birthday.day)
            )
            if years <= 0:
                months = (today.year - self.birthday.year) * 12 + today.month - self.birthday.month
                if (today.day < self.birthday.day):
                    months -= 1
                months = max(months, 0)
                return f'{months} month{"s" if months != 1 else ""}'
            return f'{years} year{"s" if years != 1 else ""}'
        if self.age_years:
            return f'~{self.age_years} year{"s" if self.age_years != 1 else ""}'
        return 'Age unknown'


class AdoptionApplication(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    cat = models.ForeignKey(Cat, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications',
    )
    message = models.TextField(help_text='Why do you want to adopt this cat?')
    living_situation = models.TextField(help_text='Housing, other pets, experience with cats, etc.')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ('cat', 'applicant')

    def __str__(self):
        return f'{self.applicant.username} → {self.cat.name} ({self.status})'


class Donation(models.Model):
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='donations',
    )
    foundation = models.ForeignKey(
        Foundation,
        on_delete=models.CASCADE,
        related_name='donations',
    )
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField(blank=True)
    is_anonymous = models.BooleanField(
        default=False,
        help_text="Hide donor name/email from the foundation. You'll still see it on your own dashboard.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} → {self.foundation.name} (₱{self.amount})'


class CatIncident(models.Model):
    TYPE_INJURED = 'injured'
    TYPE_SICK = 'sick'
    TYPE_ABANDONED = 'abandoned'
    TYPE_MISSING = 'missing'
    TYPE_UPDATE_INFO = 'update_info'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_INJURED, 'Injured'),
        (TYPE_SICK, 'Sick / needs medical help'),
        (TYPE_ABANDONED, 'Abandoned / left behind'),
        (TYPE_MISSING, 'Missing / not at usual spot'),
        (TYPE_UPDATE_INFO, 'Update cat info'),
        (TYPE_OTHER, 'Other concern'),
    ]
    TYPE_META = {
        TYPE_INJURED:     {'emoji': '🩹', 'color': '#E07A5F', 'label': 'Injured'},
        TYPE_SICK:        {'emoji': '🤒', 'color': '#F4A261', 'label': 'Sick / needs medical help'},
        TYPE_ABANDONED:   {'emoji': '💔', 'color': '#9B72AA', 'label': 'Abandoned / left behind'},
        TYPE_MISSING:     {'emoji': '🔍', 'color': '#457B9D', 'label': 'Missing / not at usual spot'},
        TYPE_UPDATE_INFO: {'emoji': '📝', 'color': '#2A9D8F', 'label': 'Update cat info'},
        TYPE_OTHER:       {'emoji': '⚠️', 'color': '#6C757D', 'label': 'Other concern'},
    }

    STATUS_OPEN = 'open'
    STATUS_ACKNOWLEDGED = 'acknowledged'
    STATUS_RESOLVED = 'resolved'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_ACKNOWLEDGED, 'Acknowledged'),
        (STATUS_RESOLVED, 'Resolved'),
    ]

    cat = models.ForeignKey(Cat, on_delete=models.CASCADE, related_name='incidents')
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reported_incidents',
    )
    reporter_name = models.CharField(max_length=100, blank=True, help_text='For anonymous reporters')
    reporter_email = models.EmailField(blank=True, help_text='For follow-up (optional)')
    incident_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(help_text='Describe what you observed — be as specific as possible.')
    photo = models.ImageField(upload_to='incidents/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    foundation_notes = models.TextField(
        blank=True,
        help_text='Notes added by the foundation when acknowledging or resolving.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_incidents',
    )

    class Meta:
        ordering = ['-created_at']

    def incident_type_label(self):
        return dict(self.TYPE_CHOICES).get(self.incident_type, self.incident_type)

    def __str__(self):
        return f'{self.incident_type_label()} — {self.cat.name} ({self.status})'

    def type_emoji(self):
        return self.TYPE_META.get(self.incident_type, {}).get('emoji', '⚠️')

    def type_color(self):
        return self.TYPE_META.get(self.incident_type, {}).get('color', '#6C757D')

    def reporter_display(self):
        if self.reporter:
            return self.reporter.get_full_name() or self.reporter.username
        return self.reporter_name or 'Anonymous'


class Announcement(models.Model):
    foundation = models.ForeignKey(
        Foundation,
        on_delete=models.CASCADE,
        related_name='announcements',
    )
    title = models.CharField(max_length=120)
    body = models.TextField()
    is_active = models.BooleanField(
        default=True,
        help_text='Only one active announcement per foundation is allowed. '
                  'Activating this will deactivate any other active announcement from your foundation.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.foundation.name}: {self.title}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            Announcement.objects.filter(
                foundation=self.foundation, is_active=True,
            ).exclude(pk=self.pk).update(is_active=False)
