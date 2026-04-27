import json
from io import BytesIO

from django.db import models

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from .forms import (
    AccountSettingsForm,
    AdoptionApplicationForm,
    AnnouncementForm,
    ApplicationReviewForm,
    CatForm,
    CatIncidentForm,
    CatMergeForm,
    CatReportForm,
    DonationForm,
    FeedingSiteForm,
    FoundationIncidentReviewForm,
    FoundationMemberAddForm,
    RegisterForm,
    StaffCatForm,
    StaffFoundationForm,
    StaffUserCreateForm,
    StaffUserUpdateForm,
)
from .mixins import (
    FoundationAdminRequiredMixin,
    FoundationRequiredMixin,
    StaffRequiredMixin,
)
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


# ── Public ───────────────────────────────────────────────────────────────────


class HomeView(TemplateView):
    template_name = 'Oggie/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['featured_cats'] = Cat.objects.filter(
            status__in=[Cat.STATUS_AVAILABLE, Cat.STATUS_IN_CARE]
        ).exclude(foundation__isnull=True)[:6]
        ctx['announcements'] = Announcement.objects.filter(is_active=True).select_related('foundation')[:3]
        return ctx


class CatListView(ListView):
    model = Cat
    template_name = 'Oggie/cat_list.html'
    context_object_name = 'cats'
    paginate_by = 12

    def get_queryset(self):
        qs = Cat.objects.select_related('foundation')
        status = self.request.GET.get('status')
        if status in dict(Cat.STATUS_CHOICES):
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Cat.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class CatDetailView(DetailView):
    model = Cat
    template_name = 'Oggie/cat_detail.html'
    context_object_name = 'cat'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['already_applied'] = (
            user.is_authenticated
            and AdoptionApplication.objects.filter(cat=self.object, applicant=user).exists()
        )
        ctx['feeding_sites'] = self.object.feeding_sites.all()
        ctx['open_incidents'] = self.object.incidents.filter(
            status=CatIncident.STATUS_OPEN
        ).count()
        return ctx


class FoundationListView(ListView):
    model = Foundation
    template_name = 'Oggie/foundation_list.html'
    context_object_name = 'foundations'


class FoundationDetailView(DetailView):
    model = Foundation
    template_name = 'Oggie/foundation_detail.html'
    context_object_name = 'foundation'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cats'] = self.object.cats.all()[:12]
        return ctx


class CatMapView(TemplateView):
    template_name = 'Oggie/cat_map.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sites = FeedingSite.objects.select_related('foundation').prefetch_related('cats')
        sites_data = []
        for s in sites:
            sites_data.append({
                'pk': s.pk,
                'name': s.name,
                'lat': float(s.latitude),
                'lng': float(s.longitude),
                'schedule': s.schedule,
                'point_person': s.point_persons_display(),
                'contact_details': s.contact_details,
                'foundation': s.foundation.name,
                'foundation_url': reverse('foundation_detail', kwargs={'pk': s.foundation.pk}),
                'cats': [
                    {
                        'name': c.name,
                        'url': reverse('cat_detail', kwargs={'slug': c.slug}),
                        'incident_url': reverse('cat_incident', kwargs={'slug': c.slug}),
                        'status': c.get_status_display(),
                    }
                    for c in s.cats.all()
                ],
            })

        # Only show cats that haven't been adopted — adopted cats have found a
        # home and don't need to appear on the public map.
        located_cats = Cat.objects.filter(
            found_lat__isnull=False,
            found_lng__isnull=False,
        ).exclude(status=Cat.STATUS_ADOPTED).select_related('foundation')
        reports_data = [
            {
                'slug': c.slug,
                'name': c.name,
                'lat': float(c.found_lat),
                'lng': float(c.found_lng),
                'url': reverse('cat_detail', kwargs={'slug': c.slug}),
                'incident_url': reverse('cat_incident', kwargs={'slug': c.slug}),
                'address': c.found_address or '',
                'age': c.age_display,
                'gender': c.get_gender_display(),
                'description': (c.description or '')[:180],
                'photo_url': c.photo.url if c.photo else '',
                'status_display': c.get_status_display(),
                'status': c.status,
                'foundation': c.foundation.name if c.foundation else 'Unclaimed',
                'is_verified': c.is_verified,
            }
            for c in located_cats
        ]

        ctx['feeding_sites_data'] = sites_data
        ctx['reports_data'] = reports_data
        ctx['focus_slug'] = self.request.GET.get('cat', '')
        return ctx


# ── Incident reports ─────────────────────────────────────────────────────────


class CatIncidentCreateView(CreateView):
    form_class = CatIncidentForm
    template_name = 'Oggie/cat_incident_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.cat = get_object_or_404(Cat, slug=kwargs['slug'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cat'] = self.cat
        ctx['incident_types'] = CatIncident.TYPE_META
        return ctx

    def form_valid(self, form):
        form.instance.cat = self.cat
        if self.request.user.is_authenticated:
            form.instance.reporter = self.request.user
            if not form.instance.reporter_name:
                form.instance.reporter_name = (
                    self.request.user.get_full_name() or self.request.user.username
                )
        messages.success(
            self.request,
            f'Thank you — your report for {self.cat.name} has been sent to the foundation.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('cat_detail', kwargs={'slug': self.cat.slug})


# ── Foundation incidents ──────────────────────────────────────────────────────


class FoundationIncidentListView(FoundationRequiredMixin, ListView):
    model = CatIncident
    template_name = 'Oggie/foundation/incident_list.html'
    context_object_name = 'incidents'
    paginate_by = 25

    def get_queryset(self):
        qs = CatIncident.objects.filter(
            cat__foundation=self.get_active_foundation(),
        ).select_related('cat', 'reporter')
        status = self.request.GET.get('status')
        if status in dict(CatIncident.STATUS_CHOICES):
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['open_count'] = CatIncident.objects.filter(
            cat__foundation=self.get_active_foundation(),
            status=CatIncident.STATUS_OPEN,
        ).count()
        ctx['status_choices'] = CatIncident.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class FoundationIncidentDetailView(FoundationRequiredMixin, View):
    def get_object(self):
        return get_object_or_404(
            CatIncident.objects.select_related('cat', 'reporter', 'resolved_by'),
            pk=self.kwargs['pk'],
            cat__foundation=self.get_active_foundation(),
        )

    def get(self, request, *args, **kwargs):
        incident = self.get_object()
        form = FoundationIncidentReviewForm(instance=incident)
        return render(request, 'Oggie/foundation/incident_detail.html', {
            'incident': incident, 'form': form,
        })

    def post(self, request, *args, **kwargs):
        incident = self.get_object()
        form = FoundationIncidentReviewForm(request.POST, instance=incident)
        if not form.is_valid():
            return render(request, 'Oggie/foundation/incident_detail.html', {
                'incident': incident, 'form': form,
            })
        new_status = form.cleaned_data['status']
        if new_status == CatIncident.STATUS_ACKNOWLEDGED and not incident.acknowledged_at:
            incident.acknowledged_at = timezone.now()
        if new_status == CatIncident.STATUS_RESOLVED and not incident.resolved_at:
            incident.resolved_at = timezone.now()
            incident.resolved_by = request.user
        form.save()
        messages.success(
            request,
            f'Incident for {incident.cat.name} marked as {incident.get_status_display().lower()}.',
        )
        return redirect('foundation_incident_list')


# ── Donations ────────────────────────────────────────────────────────────────


class DonationCreateView(CreateView):
    form_class = DonationForm
    template_name = 'Oggie/donation_form.html'
    success_url = reverse_lazy('donate_thanks')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile and profile.is_foundation:
                messages.info(
                    request,
                    "Foundation accounts can't make donations. Donations are for supporters of your foundation.",
                )
                return redirect('foundation_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        if user.is_authenticated:
            full_name = user.get_full_name() or user.username
            initial['name'] = full_name
            initial['email'] = user.email
        foundation_id = self.request.GET.get('foundation')
        if foundation_id and foundation_id.isdigit():
            initial['foundation'] = foundation_id
        return initial

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.donor = self.request.user
        messages.success(self.request, 'Thank you for your donation! 💛')
        return super().form_valid(form)


class DonationThanksView(TemplateView):
    template_name = 'Oggie/donation_thanks.html'


class DonationReceiptView(LoginRequiredMixin, View):
    def get(self, request, pk):
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )

        donation = get_object_or_404(Donation, pk=pk)
        if donation.donor_id != request.user.id and not request.user.is_staff:
            return HttpResponseForbidden('You can only download receipts for your own donations.')

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=LETTER,
            leftMargin=0.75*inch, rightMargin=0.75*inch,
            topMargin=0.6*inch, bottomMargin=0.6*inch,
            title=f'Oggie Donation Receipt OGG-{donation.pk:06d}',
            author='Oggie Cat Tracker',
        )
        styles = getSampleStyleSheet()
        coral = colors.HexColor('#FF8C61')
        rust = colors.HexColor('#C14E2C')
        charcoal = colors.HexColor('#3B2E2A')
        paw = colors.HexColor('#8B5A3C')
        cream = colors.HexColor('#FFF4E6')

        brand = ParagraphStyle(
            'brand', parent=styles['Title'],
            fontName='Helvetica-Bold', fontSize=26, textColor=rust,
            alignment=TA_LEFT, leading=30, spaceAfter=0,
        )
        tagline = ParagraphStyle(
            'tagline', parent=styles['Normal'],
            fontName='Helvetica-Oblique', fontSize=10, textColor=paw,
            alignment=TA_LEFT, leading=12,
        )
        contact = ParagraphStyle(
            'contact', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9, textColor=charcoal,
            alignment=TA_RIGHT, leading=12,
        )
        doc_title = ParagraphStyle(
            'doctitle', parent=styles['Heading1'],
            fontName='Helvetica-Bold', fontSize=16, textColor=charcoal,
            alignment=TA_CENTER, spaceBefore=12, spaceAfter=2,
        )
        doc_sub = ParagraphStyle(
            'docsub', parent=styles['Normal'],
            fontName='Helvetica', fontSize=10, textColor=paw,
            alignment=TA_CENTER, spaceAfter=14,
        )
        body = ParagraphStyle(
            'body', parent=styles['BodyText'],
            fontName='Helvetica', fontSize=11, textColor=charcoal, leading=15,
        )
        footer = ParagraphStyle(
            'footer', parent=styles['Italic'],
            fontName='Helvetica-Oblique', fontSize=8.5, textColor=paw,
            alignment=TA_CENTER, leading=11,
        )
        amount_big = ParagraphStyle(
            'amountbig', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=20, textColor=rust,
            alignment=TA_LEFT,
        )

        story = []

        # ── Letterhead ─────────────────────────────────────────────
        letterhead_left = [
            Paragraph('Oggie', brand),
            Paragraph('A portal for tracking &amp; rehoming stray cats', tagline),
        ]
        letterhead_right = [
            Paragraph('Oggie Cat Tracker', contact),
            Paragraph('hello@oggie.care', contact),
            Paragraph('www.oggie.care', contact),
        ]
        lh = Table(
            [[letterhead_left, letterhead_right]],
            colWidths=[3.6*inch, 3.4*inch],
        )
        lh.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(lh)
        story.append(Spacer(1, 0.1*inch))
        story.append(HRFlowable(width='100%', thickness=2, color=coral, spaceBefore=2, spaceAfter=6))

        # ── Document title ─────────────────────────────────────────
        story.append(Paragraph('OFFICIAL DONATION RECEIPT', doc_title))
        story.append(Paragraph(
            f'Receipt No. OGG-{donation.pk:06d} &nbsp;·&nbsp; Issued {donation.created_at.strftime("%B %d, %Y")}',
            doc_sub,
        ))

        # ── Issued-to block ────────────────────────────────────────
        # Anonymity is only for the foundation's view — the donor (the only person
        # who can download this receipt besides staff) always sees their real name.
        name_display = donation.name
        email_display = donation.email or '—'
        issued_rows = [
            [Paragraph('<b>Issued to</b>', body), Paragraph(name_display, body)],
            [Paragraph('<b>Email</b>', body), Paragraph(email_display, body)],
            [Paragraph('<b>Beneficiary</b>', body), Paragraph(donation.foundation.name, body)],
            [Paragraph('<b>Date of donation</b>', body), Paragraph(donation.created_at.strftime('%B %d, %Y'), body)],
        ]
        issued = Table(issued_rows, colWidths=[1.6*inch, 5.1*inch])
        issued.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('LINEBELOW', (0, 0), (-1, -2), 0.25, colors.HexColor('#E8D4BE')),
        ]))
        story.append(issued)
        story.append(Spacer(1, 0.25*inch))

        # ── Amount box ─────────────────────────────────────────────
        amount_box = Table(
            [[Paragraph('<b>Amount received</b>', body),
              Paragraph(f'PHP {donation.amount:,.2f}', amount_big)]],
            colWidths=[2.4*inch, 4.3*inch],
        )
        amount_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), cream),
            ('BOX', (0, 0), (-1, -1), 1.5, coral),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(amount_box)
        story.append(Spacer(1, 0.25*inch))

        if donation.message:
            story.append(Paragraph('<b>Message from the donor</b>', body))
            story.append(Paragraph(
                f'&ldquo;<i>{donation.message}</i>&rdquo;',
                ParagraphStyle('quote', parent=body, leftIndent=16, textColor=paw),
            ))
            story.append(Spacer(1, 0.2*inch))

        # ── Acknowledgement ────────────────────────────────────────
        story.append(Paragraph(
            f'<b>Thank you for your generosity.</b> Your donation will directly support the food, '
            f'medical, and shelter needs of the stray cats cared for by <b>{donation.foundation.name}</b>. '
            f'We are deeply grateful for your kindness.',
            body,
        ))
        story.append(Spacer(1, 0.4*inch))

        # ── Signature ──────────────────────────────────────────────
        sig = Table(
            [
                [Paragraph('_______________________________', body)],
                [Paragraph('<b>Oggie Cat Tracker</b>', body)],
                [Paragraph('Authorized Representative', ParagraphStyle('sigsub', parent=body, textColor=paw, fontSize=9))],
            ],
            colWidths=[3*inch],
        )
        sig.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(sig)

        # ── Footer ─────────────────────────────────────────────────
        story.append(Spacer(1, 0.5*inch))
        story.append(HRFlowable(width='100%', thickness=0.6, color=paw, spaceBefore=2, spaceAfter=6))
        story.append(Paragraph(
            'This receipt was automatically generated by the Oggie portal. '
            'Oggie is a demonstration project — no real payment has been processed. '
            'Please retain this document for your records.',
            footer,
        ))

        doc.build(story)
        pdf = buf.getvalue()
        buf.close()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="oggie-receipt-{donation.pk:06d}.pdf"'
        return response


# ── Auth ─────────────────────────────────────────────────────────────────────


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, f'Welcome, {self.object.username}! 🐾')
        return response


class AccountSettingsView(LoginRequiredMixin, UpdateView):
    form_class = AccountSettingsForm
    template_name = 'Oggie/account_settings.html'
    success_url = reverse_lazy('account_settings')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Your account has been updated.')
        return super().form_valid(form)


def post_login_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_staff:
        return redirect('staff_dashboard')
    profile = getattr(request.user, 'profile', None)
    if profile and profile.is_foundation:
        return redirect('foundation_dashboard')
    return redirect('my_dashboard')


# ── Adopter dashboard + applications ─────────────────────────────────────────


class MyDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'Oggie/my_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        apps_qs = (
            AdoptionApplication.objects
            .filter(applicant=self.request.user)
            .select_related('cat', 'cat__foundation')
        )
        app_status = self.request.GET.get('app_status', '')
        if app_status in dict(AdoptionApplication.STATUS_CHOICES):
            apps_qs = apps_qs.filter(status=app_status)
        ctx['applications'] = apps_qs
        ctx['app_status'] = app_status
        ctx['app_status_choices'] = AdoptionApplication.STATUS_CHOICES

        ctx['donations'] = (
            Donation.objects
            .filter(donor=self.request.user)
            .select_related('foundation')
        )
        ctx['reported_cats'] = (
            Cat.objects.filter(reported_by=self.request.user).select_related('foundation')
        )
        return ctx


class AdoptionApplicationCreateView(LoginRequiredMixin, CreateView):
    form_class = AdoptionApplicationForm
    template_name = 'Oggie/adoptionapplication_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.cat = get_object_or_404(Cat, slug=kwargs['slug'])
        if self.cat.foundation_id is None:
            messages.warning(request, f'{self.cat.name} has not been claimed by a foundation yet.')
            return redirect('cat_detail', slug=self.cat.slug)
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile and profile.is_foundation:
                return HttpResponseForbidden('Foundation accounts cannot submit adoption applications.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cat'] = self.cat
        return ctx

    def form_valid(self, form):
        form.instance.cat = self.cat
        form.instance.applicant = self.request.user
        if AdoptionApplication.objects.filter(cat=self.cat, applicant=self.request.user).exists():
            messages.warning(self.request, 'You have already applied to adopt this cat.')
            return redirect('cat_detail', slug=self.cat.slug)
        messages.success(self.request, f'Your application to adopt {self.cat.name} has been submitted!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('my_dashboard')


class ReportCatView(LoginRequiredMixin, CreateView):
    form_class = CatReportForm
    template_name = 'Oggie/cat_report_form.html'

    def form_valid(self, form):
        form.instance.reported_by = self.request.user
        form.instance.status = Cat.STATUS_STRAY
        form.instance.foundation = None
        messages.success(
            self.request,
            'Thank you for reporting! A partner foundation will review and verify this report soon.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('cat_detail', kwargs={'slug': self.object.slug})


# ── Foundation dashboard ─────────────────────────────────────────────────────


class FoundationDashboardView(FoundationRequiredMixin, TemplateView):
    template_name = 'Oggie/foundation/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        foundation = self.get_active_foundation()
        ctx['foundation'] = foundation
        ctx['is_admin'] = self.request.user.profile.is_admin_of(foundation)
        ctx['member_count'] = foundation.members.count()
        ctx['cat_count'] = foundation.cats.count()
        ctx['available_count'] = foundation.cats.filter(status=Cat.STATUS_AVAILABLE).count()
        ctx['pending_apps'] = (
            AdoptionApplication.objects
            .filter(cat__foundation=foundation, status=AdoptionApplication.STATUS_PENDING)
            .select_related('cat', 'applicant')[:5]
        )
        ctx['recent_donations'] = foundation.donations.all()[:5]
        ctx['donation_total'] = sum((d.amount for d in foundation.donations.all()), 0)
        ctx['unclaimed_count'] = Cat.objects.filter(foundation__isnull=True).count()
        ctx['open_incidents'] = CatIncident.objects.filter(
            cat__foundation=foundation,
            status=CatIncident.STATUS_OPEN,
        ).select_related('cat')[:5]
        ctx['open_incident_count'] = CatIncident.objects.filter(
            cat__foundation=foundation,
            status=CatIncident.STATUS_OPEN,
        ).count()
        return ctx


# ── Foundation cat actions ──────────────────────────────────────────────────


class FoundationCatClaimView(FoundationRequiredMixin, View):
    """Foundation user claims an unclaimed (foundation=None) cat."""
    def post(self, request, *args, **kwargs):
        cat = get_object_or_404(Cat, slug=kwargs['slug'])
        if cat.foundation_id is not None:
            messages.warning(request, f'{cat.name} is already claimed by {cat.foundation.name}.')
            return redirect('cat_detail', slug=cat.slug)
        target_foundation = self.get_active_foundation()
        if not target_foundation:
            messages.error(request, 'You are not associated with any foundation yet.')
            return redirect('cat_detail', slug=cat.slug)
        cat.foundation = target_foundation
        if cat.status == Cat.STATUS_STRAY:
            cat.status = Cat.STATUS_IN_CARE
        cat.save()
        messages.success(request, f'You have claimed {cat.name} for {cat.foundation.name}. 🐾')
        return redirect('cat_detail', slug=cat.slug)


# ── Foundation member management (admin-only) ──────────────────────────────


class FoundationMemberListView(FoundationAdminRequiredMixin, TemplateView):
    template_name = 'Oggie/foundation/member_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        f = self.get_active_foundation()
        ctx['foundation'] = f
        ctx['members'] = [p.user for p in f.members.select_related('user').all()]
        ctx['admin_ids'] = set(f.admins.values_list('pk', flat=True))
        return ctx


class FoundationMemberAddView(FoundationAdminRequiredMixin, View):
    template_name = 'Oggie/foundation/member_add.html'

    def get_form_kwargs(self, data=None):
        return {'foundation': self.get_active_foundation(), 'data': data}

    def get(self, request, *args, **kwargs):
        form = FoundationMemberAddForm(**self.get_form_kwargs())
        return render(request, self.template_name, {
            'form': form, 'foundation': self.get_active_foundation(),
        })

    def post(self, request, *args, **kwargs):
        f = self.get_active_foundation()
        form = FoundationMemberAddForm(**self.get_form_kwargs(data=request.POST))
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'foundation': f})
        users = form.cleaned_data['users']
        make_admin = form.cleaned_data.get('make_admin', False)
        for u in users:
            u.profile.foundations.add(f)
            if u.profile.role == u.profile.ROLE_ADOPTER:
                u.profile.role = u.profile.ROLE_FOUNDATION
                u.profile.save()
            if make_admin:
                f.admins.add(u)
        names = ', '.join(u.get_full_name() or u.username for u in users)
        suffix = ' as admin(s)' if make_admin else ''
        messages.success(request, f'Added {names} to {f.name}{suffix}.')
        return redirect('foundation_member_list')


class _MemberActionView(FoundationAdminRequiredMixin, View):
    """Shared POST handler for per-member actions. Override `act()`."""

    def post(self, request, user_id):
        f = self.get_active_foundation()
        target = get_object_or_404(User, pk=user_id)
        if target not in [p.user for p in f.members.all()]:
            messages.error(request, 'That user is not a member of this foundation.')
            return redirect('foundation_member_list')
        if target == request.user and self.requires_different_user():
            messages.error(request, "You can't perform this action on yourself.")
            return redirect('foundation_member_list')
        self.act(request, f, target)
        return redirect('foundation_member_list')

    def requires_different_user(self):
        return True

    def act(self, request, foundation, target):
        raise NotImplementedError


class FoundationMemberRemoveView(_MemberActionView):
    def act(self, request, foundation, target):
        foundation.admins.remove(target)
        target.profile.foundations.remove(foundation)
        if (
            not target.profile.foundations.exists()
            and target.profile.role == target.profile.ROLE_FOUNDATION
        ):
            target.profile.role = target.profile.ROLE_ADOPTER
            target.profile.save()
        # Drop them as point person from any feeding site of this foundation.
        for site in foundation.feeding_sites.filter(point_persons=target):
            site.point_persons.remove(target)
        messages.info(
            request,
            f'Removed {target.get_full_name() or target.username} from {foundation.name}.',
        )


class FoundationMemberPromoteView(_MemberActionView):
    def requires_different_user(self):
        return False  # safe to promote self (no-op)

    def act(self, request, foundation, target):
        foundation.admins.add(target)
        messages.success(
            request,
            f'{target.get_full_name() or target.username} is now an admin of {foundation.name}.',
        )


class FoundationMemberDemoteView(_MemberActionView):
    def act(self, request, foundation, target):
        # Guard: don't strip the last admin — the foundation would be locked out.
        if foundation.admins.count() <= 1 and foundation.admins.filter(pk=target.pk).exists():
            messages.error(
                request,
                f"Can't remove admin status — {foundation.name} needs at least one admin. "
                "Promote another member first.",
            )
            return
        foundation.admins.remove(target)
        messages.info(
            request,
            f'{target.get_full_name() or target.username} is no longer an admin.',
        )


# ── Foundation cat CRUD ──────────────────────────────────────────────────────


class FoundationCatListView(FoundationRequiredMixin, ListView):
    model = Cat
    template_name = 'Oggie/foundation/cat_list.html'
    context_object_name = 'cats'
    paginate_by = 20

    def get_queryset(self):
        return Cat.objects.filter(foundation=self.get_active_foundation())


class FoundationCatCreateView(FoundationRequiredMixin, CreateView):
    form_class = CatForm
    template_name = 'Oggie/foundation/cat_form.html'
    success_url = reverse_lazy('foundation_cat_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['foundation'] = self.get_active_foundation()
        return kwargs

    def form_valid(self, form):
        form.instance.foundation = self.get_active_foundation()
        messages.success(self.request, f'{form.instance.name} has been added!')
        return super().form_valid(form)


class FoundationCatUpdateView(FoundationRequiredMixin, UpdateView):
    form_class = CatForm
    template_name = 'Oggie/foundation/cat_form.html'
    success_url = reverse_lazy('foundation_cat_list')

    def get_queryset(self):
        return Cat.objects.filter(foundation=self.get_active_foundation())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['foundation'] = self.get_active_foundation()
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'{form.instance.name} has been updated.')
        return super().form_valid(form)


class FoundationCatDeleteView(FoundationRequiredMixin, DeleteView):
    template_name = 'Oggie/foundation/cat_confirm_delete.html'
    success_url = reverse_lazy('foundation_cat_list')

    def get_queryset(self):
        return Cat.objects.filter(foundation=self.get_active_foundation())

    def form_valid(self, form):
        messages.success(self.request, f'{self.get_object().name} has been removed.')
        return super().form_valid(form)


# ── Foundation application review ────────────────────────────────────────────


class FoundationApplicationListView(FoundationRequiredMixin, ListView):
    model = AdoptionApplication
    template_name = 'Oggie/foundation/application_list.html'
    context_object_name = 'applications'
    paginate_by = 20

    def get_queryset(self):
        qs = AdoptionApplication.objects.filter(
            cat__foundation=self.get_active_foundation()
        ).select_related('cat', 'applicant')

        status = self.request.GET.get('status')
        if status in dict(AdoptionApplication.STATUS_CHOICES):
            qs = qs.filter(status=status)

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                models.Q(cat__name__icontains=q) |
                models.Q(applicant__first_name__icontains=q) |
                models.Q(applicant__last_name__icontains=q) |
                models.Q(applicant__username__icontains=q)
            )

        sort = self.request.GET.get('sort', '-submitted_at')
        if sort in ('submitted_at', '-submitted_at'):
            qs = qs.order_by(sort)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = AdoptionApplication.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        ctx['sort'] = self.request.GET.get('sort', '-submitted_at')
        return ctx


class FoundationApplicationDetailView(FoundationRequiredMixin, View):
    def get_object(self):
        return get_object_or_404(
            AdoptionApplication.objects.select_related('cat', 'applicant'),
            pk=self.kwargs['pk'],
            cat__foundation=self.get_active_foundation(),
        )

    def get(self, request, *args, **kwargs):
        app = self.get_object()
        return render(request, 'Oggie/foundation/application_detail.html', {
            'application': app,
            'review_form': ApplicationReviewForm(),
        })

    def post(self, request, *args, **kwargs):
        app = self.get_object()
        form = ApplicationReviewForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Invalid action.')
            return redirect('foundation_application_detail', pk=app.pk)

        if app.status != AdoptionApplication.STATUS_PENDING:
            messages.warning(request, 'This application has already been reviewed.')
            return redirect('foundation_application_detail', pk=app.pk)

        action = form.cleaned_data['action']
        if action == 'approve':
            app.status = AdoptionApplication.STATUS_APPROVED
            app.reviewed_at = timezone.now()
            app.save()
            app.cat.status = Cat.STATUS_ADOPTED
            app.cat.save()
            AdoptionApplication.objects.filter(
                cat=app.cat, status=AdoptionApplication.STATUS_PENDING
            ).exclude(pk=app.pk).update(
                status=AdoptionApplication.STATUS_REJECTED,
                reviewed_at=timezone.now(),
            )
            messages.success(request, f'Application approved. {app.cat.name} is now adopted!')
        elif action == 'reject':
            app.status = AdoptionApplication.STATUS_REJECTED
            app.reviewed_at = timezone.now()
            app.save()
            messages.info(request, 'Application rejected.')
        return redirect('foundation_application_detail', pk=app.pk)


class FoundationDonationListView(FoundationRequiredMixin, ListView):
    model = Donation
    template_name = 'Oggie/foundation/donation_list.html'
    context_object_name = 'donations'
    paginate_by = 20

    def get_queryset(self):
        return Donation.objects.filter(
            foundation=self.get_active_foundation()
        ).select_related('donor')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total'] = sum((d.amount for d in self.get_queryset()), 0)
        return ctx


# ── Foundation announcements CRUD ───────────────────────────────────────────


class FoundationAnnouncementListView(FoundationRequiredMixin, ListView):
    model = Announcement
    template_name = 'Oggie/foundation/announcement_list.html'
    context_object_name = 'announcements'

    def get_queryset(self):
        return Announcement.objects.filter(foundation=self.get_active_foundation())


class FoundationAnnouncementCreateView(FoundationRequiredMixin, CreateView):
    form_class = AnnouncementForm
    template_name = 'Oggie/foundation/announcement_form.html'
    success_url = reverse_lazy('foundation_announcement_list')

    def form_valid(self, form):
        form.instance.foundation = self.get_active_foundation()
        messages.success(self.request, 'Announcement posted!')
        return super().form_valid(form)


class FoundationAnnouncementUpdateView(FoundationRequiredMixin, UpdateView):
    form_class = AnnouncementForm
    template_name = 'Oggie/foundation/announcement_form.html'
    success_url = reverse_lazy('foundation_announcement_list')

    def get_queryset(self):
        return Announcement.objects.filter(foundation=self.get_active_foundation())


class FoundationAnnouncementDeleteView(FoundationRequiredMixin, DeleteView):
    template_name = 'Oggie/foundation/announcement_confirm_delete.html'
    success_url = reverse_lazy('foundation_announcement_list')

    def get_queryset(self):
        return Announcement.objects.filter(foundation=self.get_active_foundation())


# ── Foundation feeding sites CRUD ───────────────────────────────────────────


class FoundationFeedingSiteListView(FoundationRequiredMixin, ListView):
    model = FeedingSite
    template_name = 'Oggie/foundation/feeding_site_list.html'
    context_object_name = 'sites'

    def get_queryset(self):
        return FeedingSite.objects.filter(foundation=self.get_active_foundation())


class FoundationFeedingSiteCreateView(FoundationRequiredMixin, CreateView):
    form_class = FeedingSiteForm
    template_name = 'Oggie/foundation/feeding_site_form.html'
    success_url = reverse_lazy('foundation_feeding_site_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['foundation'] = self.get_active_foundation()
        return kwargs

    def form_valid(self, form):
        form.instance.foundation = self.get_active_foundation()
        messages.success(self.request, f'Feeding site "{form.instance.name}" added!')
        return super().form_valid(form)


class FoundationFeedingSiteUpdateView(FoundationRequiredMixin, UpdateView):
    form_class = FeedingSiteForm
    template_name = 'Oggie/foundation/feeding_site_form.html'
    success_url = reverse_lazy('foundation_feeding_site_list')

    def get_queryset(self):
        return FeedingSite.objects.filter(foundation=self.get_active_foundation())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['foundation'] = self.get_active_foundation()
        return kwargs


class FoundationFeedingSiteDeleteView(FoundationRequiredMixin, DeleteView):
    template_name = 'Oggie/foundation/feeding_site_confirm_delete.html'
    success_url = reverse_lazy('foundation_feeding_site_list')

    def get_queryset(self):
        return FeedingSite.objects.filter(foundation=self.get_active_foundation())


# ── Staff admin panel ───────────────────────────────────────────────────────


class StaffDashboardView(StaffRequiredMixin, TemplateView):
    template_name = 'Oggie/staff/dashboard.html'
    extra_context = {'staff_active': 'dashboard'}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['foundation_count'] = Foundation.objects.count()
        ctx['user_count'] = User.objects.count()
        ctx['cat_count'] = Cat.objects.count()
        ctx['unclaimed_cats'] = Cat.objects.filter(foundation__isnull=True)
        return ctx


class StaffFoundationListView(StaffRequiredMixin, ListView):
    model = Foundation
    template_name = 'Oggie/staff/foundation_list.html'
    context_object_name = 'foundations'
    extra_context = {'staff_active': 'foundations'}


class StaffFoundationCreateView(StaffRequiredMixin, CreateView):
    form_class = StaffFoundationForm
    template_name = 'Oggie/staff/foundation_form.html'
    success_url = reverse_lazy('staff_foundation_list')
    extra_context = {'staff_active': 'foundations'}

    def form_valid(self, form):
        messages.success(self.request, f'Foundation "{form.instance.name}" created.')
        return super().form_valid(form)


class StaffFoundationUpdateView(StaffRequiredMixin, UpdateView):
    model = Foundation
    form_class = StaffFoundationForm
    template_name = 'Oggie/staff/foundation_form.html'
    success_url = reverse_lazy('staff_foundation_list')
    extra_context = {'staff_active': 'foundations'}


class StaffUserListView(StaffRequiredMixin, ListView):
    model = User
    template_name = 'Oggie/staff/user_list.html'
    context_object_name = 'users'
    paginate_by = 30
    extra_context = {'staff_active': 'users'}

    def get_queryset(self):
        return (
            User.objects
            .select_related('profile')
            .prefetch_related('profile__foundations')
            .order_by('username')
        )


class StaffUserCreateView(StaffRequiredMixin, CreateView):
    form_class = StaffUserCreateForm
    template_name = 'Oggie/staff/user_form.html'
    success_url = reverse_lazy('staff_user_list')
    extra_context = {'staff_active': 'users'}

    def form_valid(self, form):
        messages.success(self.request, f'User "{form.cleaned_data["username"]}" created.')
        return super().form_valid(form)


class StaffUserUpdateView(StaffRequiredMixin, UpdateView):
    model = User
    form_class = StaffUserUpdateForm
    template_name = 'Oggie/staff/user_form.html'
    success_url = reverse_lazy('staff_user_list')
    extra_context = {'staff_active': 'users'}

    def form_valid(self, form):
        messages.success(self.request, f'User "{form.instance.username}" updated.')
        return super().form_valid(form)


class StaffCatListView(StaffRequiredMixin, ListView):
    model = Cat
    template_name = 'Oggie/staff/cat_list.html'
    context_object_name = 'cats'
    paginate_by = 30
    extra_context = {'staff_active': 'cats'}

    def get_queryset(self):
        qs = Cat.objects.select_related('foundation', 'reported_by')
        if self.request.GET.get('unclaimed'):
            qs = qs.filter(foundation__isnull=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['unclaimed_only'] = bool(self.request.GET.get('unclaimed'))
        return ctx


class StaffCatUpdateView(StaffRequiredMixin, UpdateView):
    model = Cat
    form_class = StaffCatForm
    template_name = 'Oggie/staff/cat_form.html'
    success_url = reverse_lazy('staff_cat_list')
    extra_context = {'staff_active': 'cats'}

    def form_valid(self, form):
        messages.success(self.request, f'{form.instance.name} updated.')
        return super().form_valid(form)


class StaffCatMergeView(StaffRequiredMixin, View):
    """Merge a (usually reported-stray) cat into an existing profile, then delete the source."""
    template_name = 'Oggie/staff/cat_merge.html'

    def get_source(self):
        return get_object_or_404(Cat, slug=self.kwargs['slug'])

    def get(self, request, *args, **kwargs):
        source = self.get_source()
        form = CatMergeForm(source=source)
        return render(request, self.template_name, {
            'source': source,
            'form': form,
            'staff_active': 'cats',
        })

    def post(self, request, *args, **kwargs):
        source = self.get_source()
        form = CatMergeForm(request.POST, source=source)
        if not form.is_valid():
            return render(request, self.template_name, {
                'source': source, 'form': form, 'staff_active': 'cats',
            })
        target = form.cleaned_data['target']
        prefer_source = form.cleaned_data.get('prefer_source', False)

        def copy_field(field, together=()):
            """Copy source.field onto target.field based on the prefer_source flag.

            Default behavior fills in blanks on the target; with prefer_source, any
            non-empty source value overwrites. `together` lets paired fields (like
            lat/lng) stay in sync.
            """
            src_val = getattr(source, field)
            tgt_val = getattr(target, field)
            if src_val in (None, '', 0):
                return
            should_copy = (not tgt_val) or (prefer_source and src_val != tgt_val)
            if should_copy:
                setattr(target, field, src_val)
                for other in together:
                    setattr(target, other, getattr(source, other))

        copy_field('found_lat', together=('found_lng',))
        copy_field('found_address')
        copy_field('description')

        # Photo is special: reassigning the FieldFile to target then clearing source's
        # reference prevents the pre_save/post_delete signals from wiping the file.
        src_photo = source.photo
        if src_photo and (not target.photo or prefer_source):
            target.photo = src_photo
            source.photo = None

        # If target has no reporter info, inherit it from the source. Keeps the
        # community credit alive when a report is merged into an older record.
        if not target.reported_by_id and source.reported_by_id:
            target.reported_by = source.reported_by

        target.save()

        # Merge M2Ms (feeding_sites, parents).
        for site in source.feeding_sites.all():
            target.feeding_sites.add(site)
        for parent in source.parents.all():
            target.parents.add(parent)

        # Re-parent source's children onto target so lineage survives the merge.
        for child in source.children.all():
            child.parents.remove(source)
            child.parents.add(target)

        source_name = source.name
        source.delete()
        messages.success(
            request,
            f'Merged "{source_name}" into "{target.name}". The duplicate record has been removed.',
        )
        return redirect('cat_detail', slug=target.slug)


class StaffCatDeleteView(StaffRequiredMixin, DeleteView):
    model = Cat
    template_name = 'Oggie/staff/confirm_delete.html'
    success_url = reverse_lazy('staff_cat_list')
    extra_context = {'staff_active': 'cats', 'delete_kind': 'cat'}

    def form_valid(self, form):
        name = self.get_object().name
        messages.success(self.request, f'Cat "{name}" has been deleted.')
        return super().form_valid(form)


class StaffFoundationDeleteView(StaffRequiredMixin, DeleteView):
    model = Foundation
    template_name = 'Oggie/staff/confirm_delete.html'
    success_url = reverse_lazy('staff_foundation_list')
    extra_context = {'staff_active': 'foundations', 'delete_kind': 'foundation'}

    def form_valid(self, form):
        name = self.get_object().name
        messages.success(self.request, f'Foundation "{name}" has been deleted.')
        return super().form_valid(form)


class StaffUserDeleteView(StaffRequiredMixin, DeleteView):
    model = User
    template_name = 'Oggie/staff/confirm_delete.html'
    success_url = reverse_lazy('staff_user_list')
    extra_context = {'staff_active': 'users', 'delete_kind': 'user'}

    def dispatch(self, request, *args, **kwargs):
        target = self.get_object()
        if target == request.user:
            messages.error(request, "You can't delete your own account.")
            return redirect('staff_user_update', pk=target.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        username = self.get_object().username
        messages.success(self.request, f'User "{username}" has been deleted.')
        return super().form_valid(form)
