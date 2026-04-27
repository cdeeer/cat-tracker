from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Announcement, AdoptionApplication, Cat, CatIncident, Donation, FeedingSite, Foundation, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    filter_horizontal = ('foundations',)


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role', 'get_foundation')

    @admin.display(description='Role')
    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except Profile.DoesNotExist:
            return '—'

    @admin.display(description='Foundations')
    def get_foundation(self, obj):
        try:
            names = [f.name for f in obj.profile.foundations.all()]
            return ', '.join(names) if names else '—'
        except Profile.DoesNotExist:
            return '—'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Foundation)
class FoundationAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_email', 'phone', 'created_at')
    search_fields = ('name', 'contact_email')


@admin.register(Cat)
class CatAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'foundation', 'gender', 'age_years', 'created_at')
    list_filter = ('status', 'foundation', 'gender')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(AdoptionApplication)
class AdoptionApplicationAdmin(admin.ModelAdmin):
    list_display = ('cat', 'applicant', 'status', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('cat__name', 'applicant__username')


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('name', 'foundation', 'amount', 'is_anonymous', 'donor', 'created_at')
    list_filter = ('foundation', 'is_anonymous')
    search_fields = ('name', 'email', 'donor__username')


@admin.register(CatIncident)
class CatIncidentAdmin(admin.ModelAdmin):
    list_display = ('cat', 'incident_type', 'status', 'reporter_display', 'created_at')
    list_filter = ('status', 'incident_type')
    search_fields = ('cat__name', 'reporter_name', 'reporter__username')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'foundation', 'is_active', 'created_at')
    list_filter = ('is_active', 'foundation')
    search_fields = ('title', 'body')


@admin.register(FeedingSite)
class FeedingSiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'foundation', 'schedule', 'contact_details')
    list_filter = ('foundation',)
    search_fields = ('name', 'contact_details')
    filter_horizontal = ('point_persons',)
