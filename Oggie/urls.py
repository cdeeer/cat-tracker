from django.urls import path

from . import views

urlpatterns = [
    # Public
    path('', views.HomeView.as_view(), name='home'),
    path('cats/', views.CatListView.as_view(), name='cat_list'),
    path('cats/report/', views.ReportCatView.as_view(), name='cat_report'),
    path('cats/<slug:slug>/', views.CatDetailView.as_view(), name='cat_detail'),
    path('cats/<slug:slug>/apply/', views.AdoptionApplicationCreateView.as_view(), name='cat_apply'),
    path('cats/<slug:slug>/claim/', views.FoundationCatClaimView.as_view(), name='cat_claim'),
    path('cats/<slug:slug>/incident/', views.CatIncidentCreateView.as_view(), name='cat_incident'),
    path('foundations/', views.FoundationListView.as_view(), name='foundation_list'),
    path('foundations/<int:pk>/', views.FoundationDetailView.as_view(), name='foundation_detail'),
    path('map/', views.CatMapView.as_view(), name='cat_map'),
    path('donate/', views.DonationCreateView.as_view(), name='donate'),
    path('donate/thanks/', views.DonationThanksView.as_view(), name='donate_thanks'),
    path('accounts/register/', views.RegisterView.as_view(), name='register'),
    path('accounts/profile/', views.post_login_redirect, name='post_login_redirect'),

    # Adopter
    path('me/', views.MyDashboardView.as_view(), name='my_dashboard'),
    path('me/settings/', views.AccountSettingsView.as_view(), name='account_settings'),
    path('me/donations/<int:pk>/receipt.pdf', views.DonationReceiptView.as_view(), name='donation_receipt'),

    # Foundation
    path('foundation/', views.FoundationDashboardView.as_view(), name='foundation_dashboard'),
    path('foundation/cats/', views.FoundationCatListView.as_view(), name='foundation_cat_list'),
    path('foundation/cats/new/', views.FoundationCatCreateView.as_view(), name='foundation_cat_create'),
    path('foundation/cats/<slug:slug>/edit/', views.FoundationCatUpdateView.as_view(), name='foundation_cat_update'),
    path('foundation/cats/<slug:slug>/delete/', views.FoundationCatDeleteView.as_view(), name='foundation_cat_delete'),
    path('foundation/applications/', views.FoundationApplicationListView.as_view(), name='foundation_application_list'),
    path('foundation/applications/<int:pk>/', views.FoundationApplicationDetailView.as_view(), name='foundation_application_detail'),
    path('foundation/donations/', views.FoundationDonationListView.as_view(), name='foundation_donation_list'),
    path('foundation/announcements/', views.FoundationAnnouncementListView.as_view(), name='foundation_announcement_list'),
    path('foundation/announcements/new/', views.FoundationAnnouncementCreateView.as_view(), name='foundation_announcement_create'),
    path('foundation/announcements/<int:pk>/edit/', views.FoundationAnnouncementUpdateView.as_view(), name='foundation_announcement_update'),
    path('foundation/announcements/<int:pk>/delete/', views.FoundationAnnouncementDeleteView.as_view(), name='foundation_announcement_delete'),
    path('foundation/incidents/', views.FoundationIncidentListView.as_view(), name='foundation_incident_list'),
    path('foundation/incidents/<int:pk>/', views.FoundationIncidentDetailView.as_view(), name='foundation_incident_detail'),
    path('foundation/members/', views.FoundationMemberListView.as_view(), name='foundation_member_list'),
    path('foundation/members/add/', views.FoundationMemberAddView.as_view(), name='foundation_member_add'),
    path('foundation/members/<int:user_id>/remove/', views.FoundationMemberRemoveView.as_view(), name='foundation_member_remove'),
    path('foundation/members/<int:user_id>/promote/', views.FoundationMemberPromoteView.as_view(), name='foundation_member_promote'),
    path('foundation/members/<int:user_id>/demote/', views.FoundationMemberDemoteView.as_view(), name='foundation_member_demote'),
    path('foundation/feeding-sites/', views.FoundationFeedingSiteListView.as_view(), name='foundation_feeding_site_list'),
    path('foundation/feeding-sites/new/', views.FoundationFeedingSiteCreateView.as_view(), name='foundation_feeding_site_create'),
    path('foundation/feeding-sites/<int:pk>/edit/', views.FoundationFeedingSiteUpdateView.as_view(), name='foundation_feeding_site_update'),
    path('foundation/feeding-sites/<int:pk>/delete/', views.FoundationFeedingSiteDeleteView.as_view(), name='foundation_feeding_site_delete'),

    # Staff admin
    path('staff/', views.StaffDashboardView.as_view(), name='staff_dashboard'),
    path('staff/foundations/', views.StaffFoundationListView.as_view(), name='staff_foundation_list'),
    path('staff/foundations/new/', views.StaffFoundationCreateView.as_view(), name='staff_foundation_create'),
    path('staff/foundations/<int:pk>/edit/', views.StaffFoundationUpdateView.as_view(), name='staff_foundation_update'),
    path('staff/foundations/<int:pk>/delete/', views.StaffFoundationDeleteView.as_view(), name='staff_foundation_delete'),
    path('staff/users/', views.StaffUserListView.as_view(), name='staff_user_list'),
    path('staff/users/new/', views.StaffUserCreateView.as_view(), name='staff_user_create'),
    path('staff/users/<int:pk>/edit/', views.StaffUserUpdateView.as_view(), name='staff_user_update'),
    path('staff/users/<int:pk>/delete/', views.StaffUserDeleteView.as_view(), name='staff_user_delete'),
    path('staff/cats/', views.StaffCatListView.as_view(), name='staff_cat_list'),
    path('staff/cats/<slug:slug>/edit/', views.StaffCatUpdateView.as_view(), name='staff_cat_update'),
    path('staff/cats/<slug:slug>/delete/', views.StaffCatDeleteView.as_view(), name='staff_cat_delete'),
    path('staff/cats/<slug:slug>/merge/', views.StaffCatMergeView.as_view(), name='staff_cat_merge'),
]
