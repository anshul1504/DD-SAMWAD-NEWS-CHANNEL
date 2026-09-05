# Desh Darpan Samvad Project Audit

Audit date: 04 September 2026  
Scope: Django website, custom ERP/auth portal, homepage UI, web stories, footer/header, translation, email OTP, security, tests, deployment readiness.

## Executive Summary

The project has a strong foundation for a Hindi-first news platform: public article publishing, categories, locations, ads, galleries, videos, web stories, live blogs, SEO metadata, sitemaps, custom OTP authentication, role groups, and a separate ERP shell are already present.

Current status is best described as **stabilized local/demo-ready, still not fully production-ready**. The public website is functional, the homepage has modern sections and story carousel behavior, OTP delivery is wired through SMTP, security defaults have been hardened for production-style envs, and OTP coverage has improved. The biggest remaining gaps are full custom ERP CRUD screens, reliable translation architecture, encoding cleanup, production infrastructure, and broader browser/UI tests.

One critical issue was fixed during this audit: `.env.example` had a real SMTP password. It has been replaced with `your-email-password-here`, and `.env.production.example` now documents production placeholders without real secrets.

## What Is Working

- Public routes exist for home, latest, trending, search, category, tag, article detail, locations, galleries, videos, web stories, live blogs, sitemap, and robots.
- Published article filtering is implemented through `ArticleQuerySet.published()` and used across public views.
- Article views increment once per browser session.
- Homepage has hero, 24hr stories, breaking ticker, latest, trending, featured, category sections, media blocks, and multiple ad spaces.
- Web story carousel supports drag scrolling, next/previous controls, local viewed-state, and clickable story detail pages.
- Custom authentication exists for login, signup, OTP verification, forgot password, reset password, and logout.
- Signup users are assigned Guest role when the Guest group exists.
- Role setup command exists for Admin, Editor, Reporter, SEO Manager, Ads Manager, Media Manager, Live Desk, and Guest.
- Separate ERP base layout exists with sidebar, header, content area, footer, role chips, and grouped module navigation.
- SMTP settings are loaded from `.env` using `python-dotenv`.
- Production-style security settings are environment driven.
- Signup no longer stores a plaintext password in the session; it creates an inactive pending user and activates after OTP verification.
- OTP records include delivery status, delivery error, IP address, user agent, expiry, attempts, and verification timestamp.
- `python manage.py test` passes with 15 tests.
- `python manage.py makemigrations --check --dry-run` reports no model migration drift.

## Critical Findings

### 1. Production Security Settings Need Correct Environment Values

Evidence:
- [config/settings.py](../config/settings.py:30) now defaults `DEBUG=False`.
- [config/settings.py](../config/settings.py:34) requires `SECRET_KEY` when `DEBUG=False`.
- [config/settings.py](../config/settings.py:160) enables SSL redirect, secure session cookie, secure CSRF cookie, and HSTS by default when `DEBUG=False`.
- `.env.example` intentionally keeps local development settings, so running `python manage.py check --deploy` with local `.env` still reports development warnings.
- `.env.production.example` has production placeholders and secure defaults.

Impact:
- Safer than the earlier state, but production is still only secure after real hosting env values are supplied.
- A weak or placeholder secret key can compromise signing, sessions, password reset tokens, and other security-critical behavior.

Recommended fix:
- Copy production values from `.env.production.example` into the hosting secret manager or real server `.env`.
- Generate a strong `SECRET_KEY`.
- Add final production `ALLOWED_HOSTS`.
- Keep local defaults only for development.
- Enable HSTS preload only after the domain and all subdomains are permanently HTTPS-ready.

### 2. Secret Was Present In `.env.example`

Evidence:
- `.env.example` previously contained the real SMTP password.
- It is now sanitized at [.env.example](../.env.example:12).

Impact:
- If pushed to GitHub before cleanup, the mailbox password would be leaked.

Recommended fix:
- Rotate the mailbox password because it may have been exposed in local history/screenshots.
- Never put real credentials in `.env.example`.
- Before first GitHub push, run a secret scan.

### 3. Translation System Is Fragile And Can Corrupt UI Text

Evidence:
- [core/views.py](../core/views.py:53) calls the free MyMemory translation API for each text item.
- Client-side code translates live DOM text from Hindi into target languages.
- PowerShell can display Hindi source text as mojibake when the terminal encoding is not UTF-8. A source scan should be used before assuming file corruption.

Impact:
- Translation depends on an external free API and can fail, rate-limit, or return malformed text.
- DOM-based translation can accidentally translate icons, scripts, brand terms, or already-translated text.
- Encoding artifacts can appear in the browser if future edits are saved with the wrong encoding.

Recommended fix:
- Move important UI labels to Django i18n or a controlled local translation dictionary.
- Keep dynamic CMS content language-aware at the model/content level.
- Add a translation cache table to avoid repeated API calls.
- Clean all mojibake strings and ensure files are saved as UTF-8.
- Add regression tests for language switching and critical templates.

### 4. Custom ERP Is A Shell, Not A Full CMS Yet

Evidence:
- ERP module listing exists at [accounts/views.py](../accounts/views.py:211).
- Add New is only a placeholder at [accounts/views.py](../accounts/views.py:227).
- The placeholder message says form builder is next at [accounts/views.py](../accounts/views.py:231).
- Module listing shows only the first 50 records via [accounts/views.py](../accounts/views.py:218).

Impact:
- Users can sign in to the custom portal, but cannot fully manage website content without Django Admin.
- The user expectation is a complete role-based ERP, so this is the largest product gap.

Recommended fix:
- Build custom CRUD modules for articles, categories/tags, ads, galleries, videos, web stories/slides, live blogs/updates, users/roles, site settings, contacts, and newsletter subscribers.
- Add role-aware create/edit/delete/publish actions.
- Add media upload handling and preview states.
- Add editorial workflow screens: draft, submitted, review, approved, published, rejected.

## High Priority Findings

### 5. OTP Login Flow Is Improved But Still Needs Operational Hardening

Evidence:
- OTP model exists at [accounts/models.py](../accounts/models.py:33).
- OTP login is email-first at [accounts/views.py](../accounts/views.py:73).
- Signup creates an inactive user before OTP verification at [accounts/views.py](../accounts/views.py:134).
- OTP throttling is implemented with cache keys at [accounts/views.py](../accounts/views.py:43).
- Login checks for a missing OTP user before calling `login()` at [accounts/views.py](../accounts/views.py:182).

Impact:
- The previous plaintext session-password issue is fixed.
- Basic resend cooldown and email/IP throttles are present.
- Production should still use a shared cache backend, logging, and monitoring so throttles work consistently across processes.

Recommended fix:
- Use Redis or another shared cache in production for OTP throttling.
- Add deeper audit/reporting around failed OTP attempts.
- Consider deleting stale inactive signup users after expiry.
- Keep expanding tests around reset/session edge cases and cache expiry.

### 6. Raw Advertisement HTML Is Rendered Safe

Evidence:
- [templates/includes/ad_slot.html](../templates/includes/ad_slot.html:5) renders `{{ ad.html_code|safe }}`.

Impact:
- Any user with ad-management access can inject arbitrary scripts into the public website.

Recommended fix:
- Restrict raw HTML ads to Super Admin only.
- Add sanitization or a whitelist.
- Prefer structured ad fields over raw HTML.
- Add Content Security Policy before production.

### 7. Test Coverage Is Too Thin

Evidence:
- `python manage.py test` now runs 15 tests.
- Tests cover public news basics, advertisement rendering behavior, and OTP login/signup/reset edge cases.

Impact:
- Coverage is meaningfully better, but ERP permissions, translation, stories, videos, galleries, live blogs, and responsive UI can still regress silently.

Recommended fix:
- Add tests for OTP flows, Guest role assignment, permission-gated modules, article workflow, sitemap, ad rendering, web story viewer, and translation endpoint.
- Add browser smoke tests for homepage/header/footer/stories on desktop and mobile.

### 8. README Is Outdated

Evidence:
- [README.md](../README.md:62) still says Django Admin is the primary CMS.
- [README.md](../README.md:23) references only `seed_demo`.

Impact:
- Setup and handover docs do not match the current custom ERP direction.

Recommended fix:
- Update README with custom ERP routes, OTP setup, role setup command, seed commands, production notes, and GitHub workflow.

## Medium Priority Findings

### 9. Homepage UI Is Ambitious But Needs Content Discipline

Evidence:
- Homepage pulls hero, latest, trending, top stories, editor picks, most read, categories, galleries, videos, web stories, day stories, and live blogs in [news/views.py](../news/views.py:32).
- Template includes many visual sections and ad slots in [templates/home.html](../templates/home.html:1).

Impact:
- Good for a modern news portal, but empty or repeated sample content can make the page feel heavy.
- Inline CSS inside the template makes iteration quick but long-term maintenance harder.

Recommended fix:
- Move homepage CSS into `static/css/main.css` once design stabilizes.
- Use real editorial images and seeded demo data only for development.
- Add section-level empty states that collapse gracefully.
- Add image size standards for hero, cards, story covers, and ads.

### 10. Context Processor Queries Run On Every Page

Evidence:
- [core/context_processors.py](../core/context_processors.py:10) queries site settings, categories, breaking articles, cities, and ads for every template render.

Impact:
- Fine for local SQLite and small data, but expensive as traffic grows.

Recommended fix:
- Cache site settings, menu categories, popular cities, and active ads.
- Keep breaking articles cached for a short TTL.

### 11. Static/Media Serving Is Development-Oriented

Evidence:
- [config/urls.py](../config/urls.py:54) always appends staticfiles URLs.
- [config/urls.py](../config/urls.py:55) always appends media serving.

Impact:
- Acceptable locally, but not production-grade.

Recommended fix:
- Serve static/media through Nginx, CDN, or object storage in production.
- Wrap development-only URL serving behind `if settings.DEBUG`.

### 12. Database Is SQLite

Evidence:
- [config/settings.py](../config/settings.py:114) uses SQLite.

Impact:
- Good for local development, not ideal for a multi-role newsroom with uploads, workflow, and traffic.

Recommended fix:
- Move production to PostgreSQL.
- Add backups and media storage strategy.

## UX/UI Audit

### Public Website

Strengths:
- Header has clear brand, search, language selector, quick actions, navigation, and breaking ticker.
- Footer is much stronger now: dark brand color, logo, links, connect area, QR, copyright, and Webfix credit.
- Homepage now has a richer newsroom feel with hero, live desk, stories, media, categories, and ads.

Issues:
- Some visible text may still show encoding artifacts if files are not truly UTF-8.
- Design currently mixes inline homepage CSS, global CSS, and older legacy classes.
- Multiple card styles can make the homepage feel box-heavy unless spacing and content hierarchy are tightened.
- Translation can affect layout and text length unpredictably.

Recommended UX improvements:
- Standardize spacing scale: 8, 12, 16, 24, 32.
- Use fewer card borders and more editorial rhythm: image-led hero, clean lists, compact rails.
- Add skeleton loading only where async content exists.
- Make story viewer feel native: progress, pause, mute if video later, swipe, close, next story.
- Add visual ad placeholders only in admin/demo; public empty ad slots should collapse.

### ERP Portal

Strengths:
- ERP no longer depends visually on website header/footer.
- Sidebar/header/footer shell exists.
- Role chips and grouped modules are present.

Issues:
- No complete CRUD yet.
- No mobile sidebar drawer yet.
- No user role management screen yet.
- No activity/audit log.
- No content workflow detail pages.

Recommended ERP menu structure:
- Dashboard
- News Desk: Articles, Drafts, Review Queue, Published, Categories, Tags
- Story Studio: 24hr Stories, Web Stories, Story Slides
- Media Library: Images, Galleries, Videos, Reels
- Live Desk: Live Blogs, Live Updates, Breaking Ticker
- Revenue: Advertisements, Campaign Slots, Sponsored Content
- Audience: Newsletter, Contacts, Search Trends, Most Read
- Access Control: Users, Roles, Guest Approvals, Permissions
- Settings: Site Settings, Footer/Header, SEO, Social Links, Email Templates
- Reports: Traffic, Content Performance, Ad Performance

## Data Model Audit

Good:
- Article model has editorial status, SEO, flags, views, relationships, location, media, and reading time.
- Ads support placement, date windows, priority, desktop/mobile images, and HTML code.
- Web stories support slides.
- Live blogs support updates.

Gaps:
- No article revision history.
- No audit trail for who published/edited/deleted.
- No multilingual fields beyond `hindi_name` for categories.
- No explicit story expiry field for 24hr stories.
- No image alt text enforcement.
- No ad impression/click tracking.
- No soft delete/archive for most content models.

Recommended additions:
- `created_by`, `updated_by`, `published_by`.
- `ArticleRevision` or history package.
- `Story.expires_at`.
- `AdvertisementImpression` and `AdvertisementClick`.
- `Language` and translated content tables if true multilingual CMS is required.

## SEO And Content Audit

Working:
- Sitemap classes exist.
- Article JSON-LD exists in article detail.
- Meta title/description fields exist on major content models.

Gaps:
- Homepage SEO strings currently show encoding artifacts in source.
- No Open Graph image fallback per article if image missing.
- Static pages are placeholders.
- No robots policy customization from settings.

Recommended fixes:
- Clean encoding.
- Add default OG image absolute URL.
- Add canonical rules for translated/language pages.
- Fill legal/static pages with real content before launch.

## Performance Audit

Risks:
- External Google Fonts and Bootstrap CDN are render-blocking.
- Translation calls can send many texts and wait on external API.
- Context processor makes multiple DB queries per page.
- Large images need compression and responsive sizes.

Recommended fixes:
- Cache global context data.
- Add image resizing/compression workflow.
- Add database indexes for high-traffic filters.
- Serve static assets from CDN in production.
- Defer non-critical scripts.

## Accessibility Audit

Good:
- Skip link exists.
- Many buttons have labels.
- Story controls have aria labels.

Gaps:
- Some icon-only buttons need consistent accessible names.
- Color contrast should be tested after final theme.
- Story viewer needs pause/play controls for motion-sensitive users.
- Keyboard flow for offcanvas and story viewer should be verified with Playwright.

## Git And Deployment Audit

Current state:
- Git repo exists but project files are untracked.
- Remote GitHub URL was provided earlier.
- `.gitignore` excludes `.env`, SQLite, media, staticfiles, pycache, logs.

Must do before GitHub push:
- Confirm `.env.example` has no secrets.
- Rotate exposed mailbox password.
- Commit a clean baseline.
- Do not commit `db.sqlite3`, `media/`, `staticfiles/`, `.env`.
- Update README.

Recommended branch flow:
- `main`: stable deployable code.
- `dev`: active development.
- feature branches for ERP modules and UI passes.

## Verification Results

Latest commands run:

```powershell
python manage.py check --deploy
python manage.py test
python manage.py makemigrations --check --dry-run
```

Results:
- Deploy check with local dev `.env`: 5 expected development warnings.
- Deploy check with production-style environment overrides: only HSTS subdomain/preload advisory warnings remained.
- Tests: 15 tests passed.
- Migrations: no changes detected.

## Priority Roadmap

### Phase 1: Stabilize Before More UI Work

- Clean encoding artifacts across Python/templates/CSS.
- Update README.
- Put production security settings into real hosting env.
- Rotate SMTP password.
- Continue expanding auth/OTP tests.
- Add portal context processor for ERP modules.

### Phase 2: Complete Custom ERP

- Build custom article CRUD with workflow.
- Build story upload/edit module with slide management.
- Build gallery/video/liveblog/ad modules.
- Build user and role approval module.
- Build site settings and footer/header management.
- Add audit logs.

### Phase 3: Production-Grade Public Website

- Finalize homepage design system.
- Collapse empty ad slots on public pages.
- Replace demo images with final image workflow.
- Add multilingual architecture properly.
- Add caching and image optimization.
- Add browser visual regression checks.

### Phase 4: Launch Readiness

- PostgreSQL production database.
- Static/media deployment plan.
- HTTPS, HSTS, secure cookies.
- Backup strategy.
- Monitoring and error logging.
- SEO content and legal pages finalized.

## Final Audit Verdict

The platform is moving in the right direction and has enough structure to become a professional news portal. The next serious milestone should not be another visual tweak; it should be **stabilization plus custom ERP CRUD**. Once encoding, security, tests, and admin workflows are handled, the public UI can be polished confidently without repeatedly breaking the foundation.
