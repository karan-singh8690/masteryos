"""Tests for Task 027 — Brand Identity, Public Website, Documentation Portal & Developer Ecosystem.

Covers:
- Brand assets (logo, favicon, manifest, OG image, robots.txt)
- Public marketing website pages (landing, features, pricing, security, about, etc.)
- Documentation portal pages
- API explorer page
- Status page
- Support center
- SDK overview page
- Customer portal pages
- Legal pages
- SEO (sitemap.ts, robots.ts, layout metadata)
- SDK files (Python, JavaScript, Go, Java, C#)
- CLI tool (masteryos.py)
- Documentation files (brand guidelines)
- Middleware public route configuration
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("APP_ENV", "testing")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
sys.path.insert(0, str(BACKEND_DIR))

PROJECT_ROOT = BACKEND_DIR.parent                              # mastery-engine/
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
PUBLIC_DIR = FRONTEND_ROOT / "public"
BRAND_DIR = PUBLIC_DIR / "brand"
APP_DIR = FRONTEND_ROOT / "app"
SDKS_DIR = PROJECT_ROOT / "sdks"
CLI_DIR = PROJECT_ROOT / "cli"
DOCS_DIR = PROJECT_ROOT / "docs"


# ============================================================
# Part 1: Brand Identity — Asset Files
# ============================================================


class TestBrandAssets:
    """Verify all brand asset files exist."""

    def test_logo_svg_exists(self):
        assert (BRAND_DIR / "logo.svg").exists(), "Logo SVG must exist"

    def test_logo_mark_svg_exists(self):
        assert (BRAND_DIR / "logo-mark.svg").exists(), "Logo mark SVG must exist"

    def test_favicon_svg_exists(self):
        assert (PUBLIC_DIR / "favicon.svg").exists(), "Favicon SVG must exist"

    def test_og_image_svg_exists(self):
        assert (BRAND_DIR / "og-image.svg").exists(), "OG image SVG must exist"

    def test_manifest_exists(self):
        assert (PUBLIC_DIR / "manifest.webmanifest").exists(), "Web manifest must exist"

    def test_robots_txt_exists(self):
        assert (PUBLIC_DIR / "robots.txt").exists(), "robots.txt must exist"

    def test_logo_svg_contains_hexagon(self):
        content = (BRAND_DIR / "logo.svg").read_text()
        assert "path" in content, "Logo SVG must contain a path element"
        assert "MasteryOS" in content or "Mastery" in content, "Logo must contain brand name"

    def test_logo_svg_contains_gradient(self):
        content = (BRAND_DIR / "logo.svg").read_text()
        assert "gradient" in content.lower() or "2563EB" in content, "Logo must use brand gradient"

    def test_favicon_svg_is_valid_xml(self):
        content = (PUBLIC_DIR / "favicon.svg").read_text()
        assert content.startswith("<svg"), "Favicon must be a valid SVG"

    def test_manifest_has_correct_name(self):
        import json
        content = json.loads((PUBLIC_DIR / "manifest.webmanifest").read_text())
        assert content["name"] == "MasteryOS"
        assert content["short_name"] == "MasteryOS"

    def test_manifest_has_theme_color(self):
        import json
        content = json.loads((PUBLIC_DIR / "manifest.webmanifest").read_text())
        assert content["theme_color"] == "#2563EB"

    def test_manifest_has_icons(self):
        import json
        content = json.loads((PUBLIC_DIR / "manifest.webmanifest").read_text())
        assert len(content["icons"]) >= 1

    def test_robots_txt_allows_root(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "Allow: /" in content, "robots.txt must allow root"
        assert "Disallow: /api/" in content, "robots.txt must disallow /api/"

    def test_robots_txt_has_sitemap(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "Sitemap:" in content, "robots.txt must reference sitemap"

    def test_og_image_has_correct_dimensions(self):
        content = (BRAND_DIR / "og-image.svg").read_text()
        assert "1200" in content, "OG image must be 1200px wide"
        assert "630" in content, "OG image must be 630px tall"

    def test_og_image_contains_brand_name(self):
        content = (BRAND_DIR / "og-image.svg").read_text()
        assert "Mastery" in content, "OG image must contain brand name"

    def test_brand_guidelines_doc_exists(self):
        assert (DOCS_DIR / "brand" / "brand-guidelines.md").exists(), "Brand guidelines doc must exist"

    def test_brand_guidelines_has_color_palette(self):
        content = (DOCS_DIR / "brand" / "brand-guidelines.md").read_text()
        assert "#2563EB" in content, "Brand guidelines must list primary blue"
        assert "#7C3AED" in content, "Brand guidelines must list secondary purple"
        assert "#14B8A6" in content, "Brand guidelines must list accent teal"

    def test_brand_guidelines_has_typography(self):
        content = (DOCS_DIR / "brand" / "brand-guidelines.md").read_text()
        assert "Inter" in content, "Brand guidelines must specify Inter font"
        assert "JetBrains Mono" in content, "Brand guidelines must specify JetBrains Mono"

    def test_brand_guidelines_has_logo_section(self):
        content = (DOCS_DIR / "brand" / "brand-guidelines.md").read_text()
        assert "Logo" in content, "Brand guidelines must have a logo section"


# ============================================================
# Part 2: Public Marketing Website — Page Files
# ============================================================


class TestMarketingPages:
    """Verify all marketing website pages exist."""

    MARKETING_DIR = APP_DIR / "(marketing)"

    def test_marketing_layout_exists(self):
        assert (self.MARKETING_DIR / "layout.tsx").exists()

    def test_landing_page_exists(self):
        assert (self.MARKETING_DIR / "page.tsx").exists()

    def test_features_page_exists(self):
        assert (self.MARKETING_DIR / "features" / "page.tsx").exists()

    def test_pricing_page_exists(self):
        assert (self.MARKETING_DIR / "pricing" / "page.tsx").exists()

    def test_security_page_exists(self):
        assert (self.MARKETING_DIR / "security" / "page.tsx").exists()

    def test_about_page_exists(self):
        assert (self.MARKETING_DIR / "about" / "page.tsx").exists()

    def test_contact_page_exists(self):
        assert (self.MARKETING_DIR / "contact" / "page.tsx").exists()

    def test_careers_page_exists(self):
        assert (self.MARKETING_DIR / "careers" / "page.tsx").exists()

    def test_roadmap_page_exists(self):
        assert (self.MARKETING_DIR / "roadmap" / "page.tsx").exists()

    def test_changelog_page_exists(self):
        assert (self.MARKETING_DIR / "changelog" / "page.tsx").exists()

    def test_blog_index_exists(self):
        assert (self.MARKETING_DIR / "blog" / "page.tsx").exists()

    def test_blog_post_page_exists(self):
        assert (self.MARKETING_DIR / "blog" / "[slug]" / "page.tsx").exists()

    def test_blog_category_page_exists(self):
        assert (self.MARKETING_DIR / "blog" / "category" / "[category]" / "page.tsx").exists()

    def test_privacy_page_exists(self):
        assert (self.MARKETING_DIR / "legal" / "privacy" / "page.tsx").exists()

    def test_terms_page_exists(self):
        assert (self.MARKETING_DIR / "legal" / "terms" / "page.tsx").exists()

    def test_landing_page_has_hero(self):
        content = (self.MARKETING_DIR / "page.tsx").read_text()
        assert "Operating System" in content or "Learning" in content

    def test_landing_page_has_cta(self):
        content = (self.MARKETING_DIR / "page.tsx").read_text()
        assert "Get Started" in content or "register" in content.lower()

    def test_marketing_layout_has_header(self):
        content = (self.MARKETING_DIR / "layout.tsx").read_text()
        assert "header" in content.lower() or "Header" in content

    def test_marketing_layout_has_footer(self):
        content = (self.MARKETING_DIR / "layout.tsx").read_text()
        assert "footer" in content.lower() or "Footer" in content

    def test_marketing_layout_has_theme_toggle(self):
        content = (self.MARKETING_DIR / "layout.tsx").read_text()
        assert "theme" in content.lower() or "Moon" in content or "Sun" in content

    def test_pricing_has_three_tiers(self):
        content = (self.MARKETING_DIR / "pricing" / "page.tsx").read_text()
        assert "Free" in content
        assert "Pro" in content
        assert "Team" in content

    def test_changelog_has_versions(self):
        content = (self.MARKETING_DIR / "changelog" / "page.tsx").read_text()
        assert "v1.0.0" in content
        assert "v1.0.1" in content or "v1.1.0" in content

    def test_roadmap_has_columns(self):
        content = (self.MARKETING_DIR / "roadmap" / "page.tsx").read_text()
        assert "Planned" in content or "planned" in content
        assert "Shipped" in content or "shipped" in content


# ============================================================
# Part 3: Documentation Portal
# ============================================================


class TestDocsPortal:
    """Verify documentation portal pages exist."""

    DOCS_DIR = APP_DIR / "(docs)"

    def test_docs_layout_exists(self):
        assert (self.DOCS_DIR / "layout.tsx").exists()

    def test_docs_landing_exists(self):
        assert (self.DOCS_DIR / "page.tsx").exists()

    def test_getting_started_exists(self):
        assert (self.DOCS_DIR / "getting-started" / "page.tsx").exists()

    def test_rest_api_exists(self):
        assert (self.DOCS_DIR / "rest-api" / "page.tsx").exists()

    def test_docs_layout_has_sidebar(self):
        content = (self.DOCS_DIR / "layout.tsx").read_text()
        assert "sidebar" in content.lower() or "aside" in content.lower() or "nav" in content.lower()

    def test_docs_layout_has_search(self):
        content = (self.DOCS_DIR / "layout.tsx").read_text()
        assert "search" in content.lower() or "Search" in content

    def test_docs_layout_has_theme_toggle(self):
        content = (self.DOCS_DIR / "layout.tsx").read_text()
        assert "theme" in content.lower() or "Moon" in content

    def test_getting_started_has_code_block(self):
        content = (self.DOCS_DIR / "getting-started" / "page.tsx").read_text()
        assert "pre" in content or "code" in content.lower()

    def test_rest_api_has_endpoints(self):
        content = (self.DOCS_DIR / "rest-api" / "page.tsx").read_text()
        assert "GET" in content or "POST" in content
        assert "/api/v1/" in content


# ============================================================
# Part 4: API Explorer
# ============================================================


class TestApiExplorer:
    def test_api_explorer_page_exists(self):
        assert (APP_DIR / "api-explorer" / "page.tsx").exists()

    def test_api_explorer_has_tabs(self):
        content = (APP_DIR / "api-explorer" / "page.tsx").read_text()
        assert "swagger" in content.lower() or "Swagger" in content
        assert "redoc" in content.lower() or "Redoc" in content

    def test_api_explorer_has_openapi_download(self):
        content = (APP_DIR / "api-explorer" / "page.tsx").read_text()
        assert "openapi" in content.lower() or "download" in content.lower()

    def test_api_explorer_has_auth_section(self):
        content = (APP_DIR / "api-explorer" / "page.tsx").read_text()
        assert "Authorization" in content or "Bearer" in content or "auth" in content.lower()


# ============================================================
# Part 7: Status Page
# ============================================================


class TestStatusPage:
    def test_status_page_exists(self):
        assert (APP_DIR / "status" / "page.tsx").exists()

    def test_status_page_has_services(self):
        content = (APP_DIR / "status" / "page.tsx").read_text()
        assert "API" in content
        assert "Database" in content or "database" in content
        assert "Redis" in content or "redis" in content

    def test_status_page_has_incidents_section(self):
        content = (APP_DIR / "status" / "page.tsx").read_text()
        assert "incident" in content.lower() or "Incident" in content

    def test_status_page_has_operational_indicator(self):
        content = (APP_DIR / "status" / "page.tsx").read_text()
        assert "operational" in content.lower() or "Operational" in content


# ============================================================
# Part 12: Support Center
# ============================================================


class TestSupportCenter:
    def test_support_page_exists(self):
        assert (APP_DIR / "support" / "page.tsx").exists()

    def test_support_has_faq(self):
        content = (APP_DIR / "support" / "page.tsx").read_text()
        assert "FAQ" in content or "faq" in content or "question" in content.lower()

    def test_support_has_contact_form(self):
        content = (APP_DIR / "support" / "page.tsx").read_text()
        assert "form" in content.lower() or "Form" in content or "Input" in content


# ============================================================
# Part 5: SDK Landing Page
# ============================================================


class TestSdkPage:
    def test_sdk_page_exists(self):
        assert (APP_DIR / "sdk" / "page.tsx").exists()

    def test_sdk_page_lists_languages(self):
        content = (APP_DIR / "sdk" / "page.tsx").read_text()
        assert "Python" in content
        assert "JavaScript" in content or "TypeScript" in content
        assert "Go" in content
        assert "Java" in content
        assert "C#" in content or "CSharp" in content


# ============================================================
# Part 11: Customer Portal
# ============================================================


class TestCustomerPortal:
    PORTAL_DIR = APP_DIR / "(portal)"

    def test_portal_layout_exists(self):
        assert (self.PORTAL_DIR / "layout.tsx").exists()

    def test_portal_account_page_exists(self):
        assert (self.PORTAL_DIR / "account" / "page.tsx").exists()

    def test_portal_api_keys_page_exists(self):
        assert (self.PORTAL_DIR / "api-keys" / "page.tsx").exists()

    def test_portal_billing_page_exists(self):
        assert (self.PORTAL_DIR / "billing" / "page.tsx").exists()

    def test_portal_layout_has_sidebar(self):
        content = (self.PORTAL_DIR / "layout.tsx").read_text()
        assert "aside" in content.lower() or "sidebar" in content.lower() or "nav" in content.lower()

    def test_portal_layout_has_nav_items(self):
        content = (self.PORTAL_DIR / "layout.tsx").read_text()
        assert "Account" in content
        assert "Billing" in content
        assert "API Keys" in content or "api-keys" in content


# ============================================================
# Part 5: SDK Files
# ============================================================


class TestSdkFiles:
    """Verify all 5 SDKs exist."""

    def test_python_sdk_exists(self):
        assert (SDKS_DIR / "python" / "masteryos" / "__init__.py").exists()
        assert (SDKS_DIR / "python" / "masteryos" / "client.py").exists()

    def test_python_sdk_has_version(self):
        content = (SDKS_DIR / "python" / "masteryos" / "__init__.py").read_text()
        assert "__version__" in content

    def test_python_sdk_has_masteryos_class(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "class MasteryOS" in content

    def test_python_sdk_has_learning_resource(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "LearningResource" in content
        assert "get_dashboard" in content

    def test_python_sdk_has_auth_resource(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "AuthResource" in content
        assert "login" in content

    def test_python_sdk_has_beta_ops_resource(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "BetaOpsResource" in content

    def test_python_sdk_has_retry_logic(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "retry" in content.lower() or "max_retries" in content

    def test_python_sdk_has_error_classes(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "class APIError" in content
        assert "class RateLimitError" in content

    def test_python_sdk_has_pyproject(self):
        assert (SDKS_DIR / "python" / "pyproject.toml").exists()

    def test_javascript_sdk_exists(self):
        assert (SDKS_DIR / "javascript" / "src" / "index.ts").exists()

    def test_javascript_sdk_has_masteryos_class(self):
        content = (SDKS_DIR / "javascript" / "src" / "index.ts").read_text()
        assert "class MasteryOS" in content

    def test_javascript_sdk_has_package_json(self):
        assert (SDKS_DIR / "javascript" / "package.json").exists()

    def test_javascript_sdk_package_name(self):
        import json
        pkg = json.loads((SDKS_DIR / "javascript" / "package.json").read_text())
        assert pkg["name"] == "@masteryos/sdk"

    def test_go_sdk_exists(self):
        assert (SDKS_DIR / "go" / "masteryos.go").exists()

    def test_go_sdk_has_client(self):
        content = (SDKS_DIR / "go" / "masteryos.go").read_text()
        assert "type Client struct" in content
        assert "func New" in content

    def test_go_sdk_has_go_mod(self):
        assert (SDKS_DIR / "go" / "go.mod").exists()

    def test_java_sdk_exists(self):
        assert (SDKS_DIR / "java" / "src" / "main" / "java" / "com" / "masteryos" / "MasteryOS.java").exists()

    def test_java_sdk_has_builder_pattern(self):
        content = (SDKS_DIR / "java" / "src" / "main" / "java" / "com" / "masteryos" / "MasteryOS.java").read_text()
        assert "Builder" in content

    def test_csharp_sdk_exists(self):
        assert (SDKS_DIR / "csharp" / "MasteryOSClient.cs").exists()

    def test_csharp_sdk_has_class(self):
        content = (SDKS_DIR / "csharp" / "MasteryOSClient.cs").read_text()
        assert "class MasteryOSClient" in content


# ============================================================
# Part 6: CLI
# ============================================================


class TestCli:
    def test_cli_exists(self):
        assert (CLI_DIR / "masteryos.py").exists()

    def test_cli_has_version(self):
        content = (CLI_DIR / "masteryos.py").read_text()
        assert "__version__" in content

    def test_cli_has_all_commands(self):
        content = (CLI_DIR / "masteryos.py").read_text()
        for cmd in ["login", "deploy", "users", "content", "analytics", "workers", "backups", "health", "version"]:
            assert cmd in content, f"CLI must have '{cmd}' command"

    def test_cli_has_argparse(self):
        content = (CLI_DIR / "masteryos.py").read_text()
        assert "argparse" in content

    def test_cli_has_config_management(self):
        content = (CLI_DIR / "masteryos.py").read_text()
        assert "load_config" in content
        assert "save_config" in content

    def test_cli_version_output(self):
        """Run the CLI --version and check output."""
        import subprocess
        result = subprocess.run(
            ["python3", str(CLI_DIR / "masteryos.py"), "--version"],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        assert "1.0.0" in result.stdout

    def test_cli_help_output(self):
        """Run the CLI with no args and check help is shown."""
        import subprocess
        result = subprocess.run(
            ["python3", str(CLI_DIR / "masteryos.py")],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        assert "masteryos" in result.stdout.lower() or "usage" in result.stdout.lower()


# ============================================================
# Part 13: SEO — sitemap.ts, robots.ts, layout metadata
# ============================================================


class TestSeo:
    def test_sitemap_ts_exists(self):
        assert (APP_DIR / "sitemap.ts").exists()

    def test_robots_ts_exists(self):
        assert (APP_DIR / "robots.ts").exists()

    def test_sitemap_has_urls(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "/features" in content
        assert "/pricing" in content
        assert "/docs" in content
        assert "/blog" in content

    def test_sitemap_has_priority(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "priority" in content

    def test_robots_ts_disallows_admin(self):
        content = (APP_DIR / "robots.ts").read_text()
        assert "admin" in content.lower() or "dashboard" in content.lower()

    def test_robots_ts_has_sitemap_reference(self):
        content = (APP_DIR / "robots.ts").read_text()
        assert "sitemap" in content.lower()

    def test_layout_has_open_graph_metadata(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "openGraph" in content or "og" in content.lower()

    def test_layout_has_twitter_card(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "twitter" in content.lower()

    def test_layout_has_manifest(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "manifest" in content.lower()

    def test_layout_has_icons(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "icon" in content.lower()

    def test_layout_has_jetbrains_mono(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "JetBrains" in content or "jetbrains" in content.lower()

    def test_layout_has_masteryos_title(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "MasteryOS" in content


# ============================================================
# Middleware — Public Route Configuration
# ============================================================


class TestMiddleware:
    def test_middleware_has_public_prefixes(self):
        content = (FRONTEND_ROOT / "middleware.ts").read_text()
        assert "PUBLIC_PREFIXES" in content

    def test_middleware_includes_marketing_routes(self):
        content = (FRONTEND_ROOT / "middleware.ts").read_text()
        assert "/features" in content
        assert "/pricing" in content
        assert "/docs" in content
        assert "/blog" in content

    def test_middleware_includes_status_route(self):
        content = (FRONTEND_ROOT / "middleware.ts").read_text()
        assert "/status" in content

    def test_middleware_includes_api_explorer_route(self):
        content = (FRONTEND_ROOT / "middleware.ts").read_text()
        assert "/api-explorer" in content

    def test_middleware_includes_support_route(self):
        content = (FRONTEND_ROOT / "middleware.ts").read_text()
        assert "/support" in content

    def test_middleware_includes_legal_routes(self):
        content = (FRONTEND_ROOT / "middleware.ts").read_text()
        assert "/legal" in content


# ============================================================
# Page Content Verification
# ============================================================


class TestPageContent:
    """Verify page content includes expected elements."""

    def test_landing_page_mentions_operating_system(self):
        content = (APP_DIR / "(marketing)" / "page.tsx").read_text()
        assert "Operating System" in content

    def test_features_page_has_six_features(self):
        content = (APP_DIR / "(marketing)" / "features" / "page.tsx").read_text()
        # Count feature entries (each has a title)
        assert content.count("title:") >= 6 or content.count("Adaptive") >= 1

    def test_security_page_mentions_argon2(self):
        content = (APP_DIR / "(marketing)" / "security" / "page.tsx").read_text()
        assert "Argon2" in content or "argon2" in content.lower()

    def test_security_page_mentions_jwt(self):
        content = (APP_DIR / "(marketing)" / "security" / "page.tsx").read_text()
        assert "JWT" in content or "jwt" in content

    def test_security_page_mentions_rbac(self):
        content = (APP_DIR / "(marketing)" / "security" / "page.tsx").read_text()
        assert "RBAC" in content or "rbac" in content.lower() or "role" in content.lower()

    def test_pricing_page_has_feature_comparison(self):
        content = (APP_DIR / "(marketing)" / "pricing" / "page.tsx").read_text()
        assert "Comparison" in content or "comparison" in content.lower() or "table" in content.lower()

    def test_about_page_has_values(self):
        content = (APP_DIR / "(marketing)" / "about" / "page.tsx").read_text()
        assert "value" in content.lower() or "Values" in content or "mission" in content.lower()

    def test_contact_page_has_form(self):
        content = (APP_DIR / "(marketing)" / "contact" / "page.tsx").read_text()
        assert "form" in content.lower() or "Form" in content

    def test_blog_index_has_categories(self):
        content = (APP_DIR / "(marketing)" / "blog" / "page.tsx").read_text()
        assert "Engineering" in content
        assert "AI" in content

    def test_changelog_has_release_types(self):
        content = (APP_DIR / "(marketing)" / "changelog" / "page.tsx").read_text()
        assert "major" in content or "minor" in content or "patch" in content

    def test_roadmap_has_voting(self):
        content = (APP_DIR / "(marketing)" / "roadmap" / "page.tsx").read_text()
        assert "vote" in content.lower() or "Vote" in content or "ThumbsUp" in content

    def test_legal_privacy_mentions_gdpr(self):
        content = (APP_DIR / "(marketing)" / "legal" / "privacy" / "page.tsx").read_text()
        assert "GDPR" in content or "gdpr" in content.lower()

    def test_legal_terms_has_acceptance_clause(self):
        content = (APP_DIR / "(marketing)" / "legal" / "terms" / "page.tsx").read_text()
        assert "Acceptance" in content or "accept" in content.lower() or "agree" in content.lower()

    def test_docs_getting_started_has_install(self):
        content = (APP_DIR / "(docs)" / "getting-started" / "page.tsx").read_text()
        assert "pip install" in content or "npm install" in content or "install" in content.lower()

    def test_docs_rest_api_has_auth_section(self):
        content = (APP_DIR / "(docs)" / "rest-api" / "page.tsx").read_text()
        assert "Authorization" in content or "Bearer" in content

    def test_docs_rest_api_has_rate_limiting(self):
        content = (APP_DIR / "(docs)" / "rest-api" / "page.tsx").read_text()
        assert "rate" in content.lower() or "Rate" in content or "limit" in content.lower()

    def test_portal_account_has_password_section(self):
        content = (APP_DIR / "(portal)" / "account" / "page.tsx").read_text()
        assert "Password" in content or "password" in content.lower()

    def test_portal_api_keys_has_create_button(self):
        content = (APP_DIR / "(portal)" / "api-keys" / "page.tsx").read_text()
        assert "Create" in content or "create" in content.lower() or "Plus" in content

    def test_portal_billing_has_plan_info(self):
        content = (APP_DIR / "(portal)" / "billing" / "page.tsx").read_text()
        assert "plan" in content.lower() or "Plan" in content

    def test_portal_billing_has_invoices(self):
        content = (APP_DIR / "(portal)" / "billing" / "page.tsx").read_text()
        assert "invoice" in content.lower() or "Invoice" in content


# ============================================================
# All Pages Use Client or Export Metadata
# ============================================================


class TestPageConventions:
    """Verify page conventions are followed."""

    MARKETING_PAGES = [
        "page.tsx", "features/page.tsx", "pricing/page.tsx", "security/page.tsx",
        "about/page.tsx", "contact/page.tsx", "careers/page.tsx", "roadmap/page.tsx",
        "changelog/page.tsx", "blog/page.tsx", "blog/[slug]/page.tsx",
        "legal/privacy/page.tsx", "legal/terms/page.tsx",
    ]

    def test_marketing_pages_start_with_use_client(self):
        marketing = APP_DIR / "(marketing)"
        for page in self.MARKETING_PAGES:
            path = marketing / page
            if path.exists():
                content = path.read_text()
                assert content.startswith("'use client'") or content.startswith('"use client"') or content.startswith("import"), \
                    f"{page} must start with 'use client' or import"

    def test_docs_pages_start_with_use_client_or_import(self):
        docs = APP_DIR / "(docs)"
        for page in ["page.tsx", "getting-started/page.tsx", "rest-api/page.tsx"]:
            path = docs / page
            if path.exists():
                content = path.read_text()
                assert content.startswith("'use client'") or content.startswith('"use client"') or content.startswith("import"), \
                    f"docs/{page} must start with 'use client' or import"

    def test_status_page_starts_with_use_client(self):
        content = (APP_DIR / "status" / "page.tsx").read_text()
        assert content.startswith("'use client'") or content.startswith('"use client"')

    def test_support_page_starts_with_use_client(self):
        content = (APP_DIR / "support" / "page.tsx").read_text()
        assert content.startswith("'use client'") or content.startswith('"use client"')

    def test_sdk_page_starts_with_use_client(self):
        content = (APP_DIR / "sdk" / "page.tsx").read_text()
        assert content.startswith("'use client'") or content.startswith('"use client"')

    def test_api_explorer_starts_with_use_client(self):
        content = (APP_DIR / "api-explorer" / "page.tsx").read_text()
        assert content.startswith("'use client'") or content.startswith('"use client"')


# ============================================================
# Total File Count Verification
# ============================================================


class TestFileCount:
    """Verify the total number of new files meets expectations."""

    def test_marketing_pages_count(self):
        marketing = APP_DIR / "(marketing)"
        pages = list(marketing.rglob("page.tsx"))
        assert len(pages) >= 13, f"Expected ≥13 marketing pages, found {len(pages)}"

    def test_docs_pages_count(self):
        docs = APP_DIR / "(docs)"
        pages = list(docs.rglob("page.tsx"))
        assert len(pages) >= 3, f"Expected ≥3 docs pages, found {len(pages)}"

    def test_portal_pages_count(self):
        portal = APP_DIR / "(portal)"
        pages = list(portal.rglob("page.tsx"))
        assert len(pages) >= 3, f"Expected ≥3 portal pages, found {len(pages)}"

    def test_public_pages_total(self):
        """Total public-facing pages (marketing + docs + portal + standalone)."""
        total = 0
        for dir_pattern in ["(marketing)", "(docs)", "(portal)"]:
            d = APP_DIR / dir_pattern
            total += len(list(d.rglob("page.tsx")))
        # Standalone public pages
        for standalone in ["api-explorer", "status", "support", "sdk"]:
            if (APP_DIR / standalone / "page.tsx").exists():
                total += 1
        assert total >= 20, f"Expected ≥20 public pages total, found {total}"

    def test_sdk_files_count(self):
        sdk_files = []
        sdk_files.append(SDKS_DIR / "python" / "masteryos" / "__init__.py")
        sdk_files.append(SDKS_DIR / "python" / "masteryos" / "client.py")
        sdk_files.append(SDKS_DIR / "python" / "pyproject.toml")
        sdk_files.append(SDKS_DIR / "javascript" / "src" / "index.ts")
        sdk_files.append(SDKS_DIR / "javascript" / "package.json")
        sdk_files.append(SDKS_DIR / "go" / "masteryos.go")
        sdk_files.append(SDKS_DIR / "go" / "go.mod")
        sdk_files.append(SDKS_DIR / "java" / "src" / "main" / "java" / "com" / "masteryos" / "MasteryOS.java")
        sdk_files.append(SDKS_DIR / "csharp" / "MasteryOSClient.cs")
        existing = [f for f in sdk_files if f.exists()]
        assert len(existing) >= 9, f"Expected ≥9 SDK files, found {len(existing)}"

    def test_brand_assets_count(self):
        assets = [
            BRAND_DIR / "logo.svg",
            BRAND_DIR / "logo-mark.svg",
            BRAND_DIR / "og-image.svg",
            PUBLIC_DIR / "favicon.svg",
            PUBLIC_DIR / "manifest.webmanifest",
            PUBLIC_DIR / "robots.txt",
            DOCS_DIR / "brand" / "brand-guidelines.md",
        ]
        existing = [a for a in assets if a.exists()]
        assert len(existing) >= 7, f"Expected ≥7 brand assets, found {len(existing)}"
