# MasteryOS Brand Guidelines

> **Version:** 1.0
> **Last updated:** 2026-07-03 (Task 027)
> **Status:** Public

---

## 1. Brand Name

**MasteryOS** — The Operating System for Learning.

The name conveys:
- **Mastery** — our core value proposition: measurable, durable mastery
- **OS** — platform-level infrastructure, not just an app
- **Short** — 9 characters, easy to type, easy to remember
- **Global** — no cultural baggage, works in all languages

### Usage
- Always write as **MasteryOS** (camelCase, no space)
- Never write as "Mastery OS", "MasteryOS.io", or "Mastery O.S."
- In code: `masteryos`, `MasteryOS`, `MASTERYOS` (constants)
- Domain: `masteryos.com`

---

## 2. Logo

### 2.1 Logo Concept
The logo combines a **hexagon** (representing the knowledge graph — concepts connected to each other) with an **upward triangle** inside (representing ascending mastery — every level builds upward).

### 2.2 Logo Variants

| Variant | File | Use case |
|---|---|---|
| Full logo (horizontal) | `public/brand/logo.svg` | Website headers, email signatures, presentations |
| Logo mark only | `public/brand/logo-mark.svg` | Favicon, app icons, social avatars |
| Favicon | `public/favicon.svg` | Browser tab |
| OG image | `public/brand/og-image.svg` | Social media sharing |

### 2.3 Clear Space
Maintain a minimum clear space equal to the height of the logo mark (the hexagon) on all sides.

### 2.4 Minimum Size
- Full logo: 120px wide (digital) / 1.2in (print)
- Logo mark: 24px (digital) / 0.25in (print)

### 2.5 What NOT to Do
- ❌ Do not stretch, compress, or rotate the logo
- ❌ Do not change the gradient colors
- ❌ Do not place the logo on busy backgrounds without sufficient contrast
- ❌ Do not add drop shadows or 3D effects
- ❌ Do not use the logo mark alone without the wordmark in formal contexts (except as favicon/app icon)

---

## 3. Color Palette

### 3.1 Primary Colors

| Name | Hex | RGB | Usage |
|---|---|---|---|
| Blue | `#2563EB` | 37, 99, 235 | Primary brand color, CTAs, links |
| Purple | `#7C3AED` | 124, 58, 237 | Secondary brand, gradients, accents |
| Teal | `#14B8A6` | 20, 184, 166 | Accent, success states, highlights |

### 3.2 Semantic Colors

| Name | Hex | RGB | Usage |
|---|---|---|---|
| Success | `#10B981` | 16, 185, 129 | Positive actions, correct answers |
| Warning | `#F59E0B` | 245, 158, 11 | Cautions, pending states |
| Danger | `#EF4444` | 239, 68, 68 | Errors, destructive actions |

### 3.3 Neutral Colors

| Name | Hex | Usage |
|---|---|---|
| Slate 900 | `#0F172A` | Dark mode background, headings |
| Slate 700 | `#334155` | Body text (dark mode) |
| Slate 500 | `#64748B` | Muted text |
| Slate 300 | `#CBD5E1` | Borders (dark mode) |
| Slate 100 | `#F1F5F9` | Light mode background |
| White | `#FFFFFF` | Light mode background, cards |

### 3.4 Gradient
The brand gradient flows from Blue → Purple → Teal:
```
linear-gradient(135deg, #2563EB 0%, #7C3AED 50%, #14B8A6 100%)
```

Used in: logo mark, hero backgrounds, primary CTAs, progress bars.

### 3.5 Color Accessibility
All color combinations meet WCAG AA contrast (4.5:1 for normal text, 3:1 for large text).

---

## 4. Typography

| Role | Font | Weights | Usage |
|---|---|---|---|
| Headings | **Inter** | 600, 700, 800 | Page titles, section headers, hero text |
| Body | **Inter** | 400, 500 | Paragraphs, UI labels, buttons |
| Code | **JetBrains Mono** | 400, 500 | Code blocks, API examples, CLI output |

### Type Scale

| Name | Size | Weight | Usage |
|---|---|---|---|
| Display | 48px | 800 | Hero headlines |
| H1 | 36px | 700 | Page titles |
| H2 | 30px | 700 | Section headers |
| H3 | 24px | 600 | Subsection headers |
| H4 | 20px | 600 | Card titles |
| Body | 16px | 400 | Paragraphs |
| Small | 14px | 400 | Secondary text |
| Caption | 12px | 500 | Labels, metadata |
| Code | 14px | 400 | Inline code, code blocks |

---

## 5. Voice & Tone

### Brand Voice
- **Professional but approachable** — we're experts, not elitists
- **Clear and concise** — every word earns its place
- **Encouraging** — learning is hard; we celebrate progress
- **Technical when needed** — we don't dumb down; we explain

### Tone by Context

| Context | Tone | Example |
|---|---|---|
| Marketing | Confident, aspirational | "Master Python interviews with adaptive learning" |
| Documentation | Clear, instructional | "To authenticate, pass your API key in the Authorization header" |
| Error messages | Helpful, actionable | "Invalid email. Check for typos and try again." |
| Success states | Celebratory, brief | "Mastery level up! You're now Proficient in async/await." |
| Support | Empathetic, solution-oriented | "Thanks for reporting this — let's get it fixed." |

### Writing Rules
- Use active voice
- Use second person ("You" not "the user")
- Keep sentences under 25 words
- Use Oxford commas
- Capitalize feature names: Mastery Engine, Study Session, Welcome Wizard
- Never use exclamation marks in error messages

---

## 6. Domain Architecture

| Subdomain | Purpose |
|---|---|
| `masteryos.com` | Marketing website + app |
| `docs.masteryos.com` | Documentation portal |
| `api.masteryos.com` | REST API |
| `beta.masteryos.com` | Closed Beta (redirects to app during beta) |
| `status.masteryos.com` | Public status page |

---

## 7. Asset Checklist

| Asset | File | Status |
|---|---|---|
| Full logo (SVG) | `public/brand/logo.svg` | ✅ |
| Logo mark (SVG) | `public/brand/logo-mark.svg` | ✅ |
| Favicon (SVG) | `public/favicon.svg` | ✅ |
| OG image (SVG) | `public/brand/og-image.svg` | ✅ |
| Web manifest | `public/manifest.webmanifest` | ✅ |
| robots.txt | `public/robots.txt` | ✅ |
| Brand guidelines | `docs/brand/brand-guidelines.md` | ✅ (this file) |

---

**MasteryOS™** is a trademark of Mastery Engine.
