# Oggie — Cat Tracker

A Django-based portal for tracking stray cats, accepting adoption applications, and collecting donations for partner foundations.

## Features

- Public gallery of stray and adoptable cats with photo, status, and care info
- Adoption applications (login required)
- Mock donation form (records intent — no real payment processing)
- Two authenticated roles:
  - **Adopter/Donor** — self-registers via the signup page
  - **Partner Foundation** — admin-created, gets a dashboard to manage cats, review applications, and see donations
- Cartoony cat-themed UI built with Fredoka + Nunito and a warm peach/coral/mint palette

## Setup

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync                        # install dependencies
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Visit <http://127.0.0.1:8000/>.

## Creating a partner foundation account

Partner foundations are not self-serve. As an admin:

1. Go to `/admin/` and log in as a superuser.
2. Under **Oggie → Foundations**, create a new Foundation (name, contact, logo, etc.).
3. Under **Users**, create a new User for that foundation.
4. On the same user page, the **Profile** inline will be shown at the bottom. Set:
   - `Role` = `Foundation Partner`
   - `Foundation` = the foundation you just created
5. Save. That user can now log in and will land on the foundation dashboard (`/foundation/`).

## Project structure

```text
cat_tracker/                 # Django project (settings, root urls)
Oggie/                       # the single app
├── models.py                # Foundation, Profile, Cat, AdoptionApplication, Donation
├── views.py                 # CBVs + FBV for post-login redirect
├── forms.py                 # Register, donation, adoption, cat, review forms
├── mixins.py                # FoundationRequiredMixin
├── signals.py               # auto-create Profile on User creation
├── admin.py                 # all models registered, Profile inline on User
├── urls.py
├── templates/
│   ├── Oggie/               # public + adopter templates, foundation/ subdir
│   └── registration/        # login.html, register.html
└── static/Oggie/            # site.css, paw/logo/hero SVGs
```

## Adding cats (as a foundation)

Log in as a foundation user → `/foundation/cats/new/` → upload a photo, set status to "Available for Adoption" to make the cat visible to adopters.

## Running tests / checks

```bash
uv run python manage.py check
uv run python manage.py test
```
