from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class FoundationRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allow only logged-in users with role='foundation' AND at least one linked Foundation.

    Views that inherit this can call `self.get_active_foundation()` to pick the foundation
    context for this request (honors `?f=<pk>` when the user belongs to multiple).
    """

    raise_exception = False

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        profile = getattr(user, 'profile', None)
        if profile is None:
            return False
        return profile.role == 'foundation' and profile.foundations.exists()

    def get_user_foundations(self):
        return self.request.user.profile.foundations.all()

    def get_active_foundation(self):
        qs = self.get_user_foundations()
        requested = self.request.GET.get('f') or self.request.POST.get('f')
        if requested and requested.isdigit():
            match = qs.filter(pk=int(requested)).first()
            if match:
                return match
        return qs.first()


class FoundationAdminRequiredMixin(FoundationRequiredMixin):
    """Same as FoundationRequiredMixin but further restricted to admins of the
    currently active foundation. Non-admin members are denied. Oggie staff
    always pass."""

    def test_func(self):
        if not super().test_func():
            return False
        if self.request.user.is_staff:
            return True
        active = self.get_active_foundation()
        return active is not None and active.admins.filter(pk=self.request.user.pk).exists()


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allow only users with is_staff=True."""

    raise_exception = False

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff
