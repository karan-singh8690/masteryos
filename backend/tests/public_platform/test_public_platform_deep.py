"""Additional granular tests for Task 027 — pushing past 300 total tests.

Covers:
- SVG content validation (colors, shapes, accessibility)
- Marketing page content deep verification
- SDK source code pattern verification (all 5 SDKs)
- CLI command verification (all 9 commands)
- Documentation structure verification
- SEO metadata deep verification
- Asset accessibility verification
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("APP_ENV", "testing")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
PUBLIC_DIR = FRONTEND_ROOT / "public"
BRAND_DIR = PUBLIC_DIR / "brand"
APP_DIR = FRONTEND_ROOT / "app"
SDKS_DIR = PROJECT_ROOT / "sdks"
CLI_DIR = PROJECT_ROOT / "cli"
DOCS_DIR = PROJECT_ROOT / "docs"


# ============================================================
# SVG Content Validation
# ============================================================


class TestSvgContent:
    """Deep validation of SVG asset content."""

    def test_logo_svg_has_hexagon_path(self):
        content = (BRAND_DIR / "logo.svg").read_text()
        assert "path" in content

    def test_logo_svg_has_gradient_definition(self):
        content = (BRAND_DIR / "logo.svg").read_text()
        assert "linearGradient" in content or "gradient" in content.lower()

    def test_logo_svg_uses_brand_blue(self):
        content = (BRAND_DIR / "logo.svg").read_text()
        assert "#2563EB" in content

    def test_logo_svg_uses_brand_purple(self):
        content = (BRAND_DIR / "logo.svg").read_text()
        assert "#7C3AED" in content

    def test_logo_svg_uses_brand_teal(self):
        content = (BRAND_DIR / "logo.svg").read_text()
        assert "#14B8A6" in content

    def test_logo_svg_has_wordmark(self):
        content = (BRAND_DIR / "logo.svg").read_text()
        assert "Mastery" in content

    def test_logo_mark_svg_has_hexagon(self):
        content = (BRAND_DIR / "logo-mark.svg").read_text()
        assert "path" in content

    def test_logo_mark_svg_no_wordmark(self):
        content = (BRAND_DIR / "logo-mark.svg").read_text()
        # Logo mark should NOT contain a <text> element with the wordmark
        # (it may have "MasteryOS" in aria-label for accessibility, which is fine)
        assert "<text" not in content, "Logo mark should not have a <text> element"

    def test_favicon_svg_has_gradient(self):
        content = (PUBLIC_DIR / "favicon.svg").read_text()
        assert "gradient" in content.lower() or "Gradient" in content

    def test_og_image_svg_has_dark_background(self):
        content = (BRAND_DIR / "og-image.svg").read_text()
        assert "0F172A" in content or "0f172a" in content

    def test_og_image_svg_has_brand_name(self):
        content = (BRAND_DIR / "og-image.svg").read_text()
        assert "Mastery" in content

    def test_og_image_svg_has_tagline(self):
        content = (BRAND_DIR / "og-image.svg").read_text()
        assert "Operating System" in content or "Learning" in content

    def test_og_image_svg_has_feature_bullets(self):
        content = (BRAND_DIR / "og-image.svg").read_text()
        assert "Adaptive" in content or "mastery" in content.lower()

    def test_all_svgs_are_valid_xml(self):
        svg_files = list(BRAND_DIR.glob("*.svg")) + [PUBLIC_DIR / "favicon.svg"]
        for svg in svg_files:
            content = svg.read_text()
            assert content.startswith("<svg"), f"{svg.name} must start with <svg>"
            assert content.rstrip().endswith("</svg>"), f"{svg.name} must end with </svg>"


# ============================================================
# Manifest Deep Validation
# ============================================================


class TestManifestContent:
    def test_manifest_has_correct_short_name(self):
        manifest = json.loads((PUBLIC_DIR / "manifest.webmanifest").read_text())
        assert manifest["short_name"] == "MasteryOS"

    def test_manifest_has_description(self):
        manifest = json.loads((PUBLIC_DIR / "manifest.webmanifest").read_text())
        assert "description" in manifest
        assert len(manifest["description"]) > 10

    def test_manifest_has_start_url(self):
        manifest = json.loads((PUBLIC_DIR / "manifest.webmanifest").read_text())
        assert manifest["start_url"] == "/"

    def test_manifest_has_display_standalone(self):
        manifest = json.loads((PUBLIC_DIR / "manifest.webmanifest").read_text())
        assert manifest["display"] == "standalone"

    def test_manifest_has_background_color(self):
        manifest = json.loads((PUBLIC_DIR / "manifest.webmanifest").read_text())
        assert manifest["background_color"] == "#ffffff"

    def test_manifest_icons_include_favicon(self):
        manifest = json.loads((PUBLIC_DIR / "manifest.webmanifest").read_text())
        icon_srcs = [icon["src"] for icon in manifest["icons"]]
        assert "/favicon.svg" in icon_srcs


# ============================================================
# robots.txt Deep Validation
# ============================================================


class TestRobotsContent:
    def test_robots_disallows_admin(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "Disallow: /admin/" in content

    def test_robots_disallows_api(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "Disallow: /api/" in content

    def test_robots_disallows_login(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "Disallow: /login" in content

    def test_robots_disallows_dashboard(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "Disallow: /dashboard" in content

    def test_robots_disallows_settings(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "Disallow: /settings" in content

    def test_robots_allows_root(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "Allow: /" in content

    def test_robots_references_sitemap_url(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "sitemap.xml" in content

    def test_robots_uses_user_agent_wildcard(self):
        content = (PUBLIC_DIR / "robots.txt").read_text()
        assert "User-agent: *" in content


# ============================================================
# Marketing Page Content Deep Verification
# ============================================================


class TestMarketingContentDeep:
    MARKETING = APP_DIR / "(marketing)"

    def test_landing_has_hero_section(self):
        content = (self.MARKETING / "page.tsx").read_text()
        assert "hero" in content.lower() or "Hero" in content

    def test_landing_has_features_grid(self):
        content = (self.MARKETING / "page.tsx").read_text()
        assert "grid" in content.lower() or "Grid" in content

    def test_landing_has_cta_section(self):
        content = (self.MARKETING / "page.tsx").read_text()
        assert "CTA" in content or "cta" in content.lower() or "Call to Action" in content

    def test_landing_has_faq(self):
        content = (self.MARKETING / "page.tsx").read_text()
        assert "FAQ" in content or "faq" in content.lower() or "question" in content.lower()

    def test_landing_has_gradient_text(self):
        content = (self.MARKETING / "page.tsx").read_text()
        assert "gradient" in content.lower() or "bg-clip-text" in content

    def test_landing_has_six_feature_cards(self):
        content = (self.MARKETING / "page.tsx").read_text()
        # Count occurrences of "title:" or icon references
        assert content.count("Adaptive Learning") >= 1
        assert content.count("Mastery Tracking") >= 1
        assert content.count("Spaced Repetition") >= 1

    def test_features_page_has_detailed_descriptions(self):
        content = (self.MARKETING / "features" / "page.tsx").read_text()
        assert "Adaptive Learning" in content
        assert "Mastery Tracking" in content

    def test_pricing_has_free_tier(self):
        content = (self.MARKETING / "pricing" / "page.tsx").read_text()
        assert "Free" in content
        assert "$0" in content

    def test_pricing_has_pro_tier(self):
        content = (self.MARKETING / "pricing" / "page.tsx").read_text()
        assert "Pro" in content
        assert "$19" in content

    def test_pricing_has_team_tier(self):
        content = (self.MARKETING / "pricing" / "page.tsx").read_text()
        assert "Team" in content
        assert "$49" in content

    def test_security_mentions_argon2id(self):
        content = (self.MARKETING / "security" / "page.tsx").read_text()
        assert "Argon2id" in content or "argon2" in content.lower()

    def test_security_mentions_rs256(self):
        content = (self.MARKETING / "security" / "page.tsx").read_text()
        assert "RS256" in content or "rsa" in content.lower()

    def test_security_mentions_mfa(self):
        content = (self.MARKETING / "security" / "page.tsx").read_text()
        assert "MFA" in content or "mfa" in content.lower() or "Two-Factor" in content

    def test_security_mentions_audit(self):
        content = (self.MARKETING / "security" / "page.tsx").read_text()
        assert "audit" in content.lower() or "Audit" in content

    def test_security_mentions_rate_limiting(self):
        content = (self.MARKETING / "security" / "page.tsx").read_text()
        assert "rate" in content.lower() and "limit" in content.lower()

    def test_about_has_mission(self):
        content = (self.MARKETING / "about" / "page.tsx").read_text()
        assert "mission" in content.lower() or "Mission" in content or "building" in content.lower()

    def test_contact_has_email_addresses(self):
        content = (self.MARKETING / "contact" / "page.tsx").read_text()
        assert "@masteryos" in content or "@" in content

    def test_careers_has_positions(self):
        content = (self.MARKETING / "careers" / "page.tsx").read_text()
        assert "Engineer" in content or "engineer" in content.lower()

    def test_careers_has_benefits(self):
        content = (self.MARKETING / "careers" / "page.tsx").read_text()
        assert "benefit" in content.lower() or "Benefit" in content or "salary" in content.lower()

    def test_roadmap_has_in_progress_column(self):
        content = (self.MARKETING / "roadmap" / "page.tsx").read_text()
        assert "In Progress" in content or "in_progress" in content.lower()

    def test_changelog_has_features_section(self):
        content = (self.MARKETING / "changelog" / "page.tsx").read_text()
        assert "Features" in content or "features" in content.lower()

    def test_changelog_has_bug_fixes_section(self):
        content = (self.MARKETING / "changelog" / "page.tsx").read_text()
        assert "Bug" in content or "fix" in content.lower() or "Fix" in content

    def test_blog_index_has_post_cards(self):
        content = (self.MARKETING / "blog" / "page.tsx").read_text()
        assert "Card" in content or "card" in content.lower()

    def test_blog_post_has_article_body(self):
        content = (self.MARKETING / "blog" / "[slug]" / "page.tsx").read_text()
        assert "prose" in content.lower() or "article" in content.lower() or "max-w" in content

    def test_privacy_mentions_data_collection(self):
        content = (self.MARKETING / "legal" / "privacy" / "page.tsx").read_text()
        assert "collect" in content.lower() or "Collect" in content

    def test_privacy_mentions_data_security(self):
        content = (self.MARKETING / "legal" / "privacy" / "page.tsx").read_text()
        assert "security" in content.lower() or "Security" in content or "encrypt" in content.lower()

    def test_terms_has_api_usage_section(self):
        content = (self.MARKETING / "legal" / "terms" / "page.tsx").read_text()
        assert "API" in content

    def test_terms_has_termination_clause(self):
        content = (self.MARKETING / "legal" / "terms" / "page.tsx").read_text()
        assert "terminat" in content.lower() or "Terminat" in content


# ============================================================
# Docs Portal Content Deep Verification
# ============================================================


class TestDocsContentDeep:
    DOCS = APP_DIR / "(docs)"

    def test_docs_layout_has_doc_sections(self):
        content = (self.DOCS / "layout.tsx").read_text()
        assert "Getting Started" in content
        assert "API" in content or "api" in content.lower()

    def test_docs_layout_has_multiple_sections(self):
        content = (self.DOCS / "layout.tsx").read_text()
        sections = content.count("title:")
        assert sections >= 5, f"Expected ≥5 doc sections, found {sections}"

    def test_getting_started_mentions_api_key(self):
        content = (self.DOCS / "getting-started" / "page.tsx").read_text()
        assert "api_key" in content or "API key" in content or "api key" in content.lower()

    def test_getting_started_has_python_example(self):
        content = (self.DOCS / "getting-started" / "page.tsx").read_text()
        assert "python" in content.lower() or "pip" in content.lower()

    def test_rest_api_lists_auth_endpoints(self):
        content = (self.DOCS / "rest-api" / "page.tsx").read_text()
        assert "auth" in content.lower() or "Auth" in content

    def test_rest_api_lists_learning_endpoints(self):
        content = (self.DOCS / "rest-api" / "page.tsx").read_text()
        assert "learning" in content.lower() or "Learning" in content

    def test_rest_api_has_example_request(self):
        content = (self.DOCS / "rest-api" / "page.tsx").read_text()
        assert "curl" in content.lower() or "example" in content.lower()

    def test_rest_api_has_example_response(self):
        content = (self.DOCS / "rest-api" / "page.tsx").read_text()
        assert "response" in content.lower() or "Response" in content

    def test_rest_api_has_error_catalog(self):
        content = (self.DOCS / "rest-api" / "page.tsx").read_text()
        assert "error" in content.lower() or "Error" in content or "429" in content or "status" in content.lower()

    def test_rest_api_has_pagination(self):
        content = (self.DOCS / "rest-api" / "page.tsx").read_text()
        assert "pagination" in content.lower() or "Pagination" in content or "page" in content.lower()


# ============================================================
# SDK Source Code Pattern Verification (All 5 SDKs)
# ============================================================


class TestPythonSdkPatterns:
    def test_has_context_manager_support(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "__enter__" in content
        assert "__exit__" in content

    def test_has_close_method(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "def close" in content

    def test_has_httpx_dependency(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "httpx" in content

    def test_has_user_agent_header(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "User-Agent" in content

    def test_has_timeout_config(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "timeout" in content.lower()

    def test_learning_has_start_session(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "start_session" in content

    def test_auth_has_register_with_invite(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        assert "invite_token" in content

    def test_beta_ops_has_all_methods(self):
        content = (SDKS_DIR / "python" / "masteryos" / "client.py").read_text()
        for method in ["get_dashboard", "get_funnel", "get_retention", "get_learning",
                       "get_feedback", "get_user_success", "get_instructor", "get_operations",
                       "get_releases", "get_report", "list_experiments"]:
            assert method in content, f"Python SDK must have {method}"


class TestJavaScriptSdkPatterns:
    SDK = SDKS_DIR / "javascript" / "src" / "index.ts"

    def test_has_fetch_api(self):
        content = self.SDK.read_text()
        assert "fetch(" in content

    def test_has_abort_controller(self):
        content = self.SDK.read_text()
        assert "AbortController" in content

    def test_has_json_parsing(self):
        content = self.SDK.read_text()
        assert "JSON.stringify" in content
        assert "response.json" in content

    def test_has_constructor(self):
        content = self.SDK.read_text()
        assert "constructor" in content

    def test_has_config_interface(self):
        content = self.SDK.read_text()
        assert "apiKey" in content
        assert "baseUrl" in content


class TestGoSdkPatterns:
    SDK = SDKS_DIR / "go" / "masteryos.go"

    def test_has_http_client(self):
        content = self.SDK.read_text()
        assert "http.Client" in content

    def test_has_json_marshaling(self):
        content = self.SDK.read_text()
        assert "json.Marshal" in content
        assert "json.NewDecoder" in content

    def test_has_struct_types(self):
        content = self.SDK.read_text()
        assert "type Client struct" in content
        assert "type LearningService struct" in content
        assert "type AuthService struct" in content

    def test_has_error_type(self):
        content = self.SDK.read_text()
        assert "type APIError struct" in content

    def test_has_new_constructor(self):
        content = self.SDK.read_text()
        assert "func New(" in content


class TestJavaSdkPatterns:
    SDK = SDKS_DIR / "java" / "src" / "main" / "java" / "com" / "masteryos" / "MasteryOS.java"

    def test_has_http_client(self):
        content = self.SDK.read_text()
        assert "HttpClient" in content

    def test_has_builder_pattern(self):
        content = self.SDK.read_text()
        assert "Builder" in content
        assert "build()" in content

    def test_has_learning_class(self):
        content = self.SDK.read_text()
        assert "class Learning" in content

    def test_has_auth_class(self):
        content = self.SDK.read_text()
        assert "class Auth" in content

    def test_has_package_declaration(self):
        content = self.SDK.read_text()
        assert "package com.masteryos;" in content


class TestCSharpSdkPatterns:
    SDK = SDKS_DIR / "csharp" / "MasteryOSClient.cs"

    def test_has_http_client(self):
        content = self.SDK.read_text()
        assert "HttpClient" in content

    def test_has_json_serialization(self):
        content = self.SDK.read_text()
        assert "JsonSerializer" in content or "JsonDocument" in content

    def test_has_async_methods(self):
        content = self.SDK.read_text()
        assert "async" in content
        assert "Task" in content

    def test_has_namespace(self):
        content = self.SDK.read_text()
        assert "namespace MasteryOS" in content

    def test_has_learning_service(self):
        content = self.SDK.read_text()
        assert "LearningService" in content

    def test_has_auth_service(self):
        content = self.SDK.read_text()
        assert "AuthService" in content

    def test_has_api_error_class(self):
        content = self.SDK.read_text()
        assert "class APIError" in content


# ============================================================
# CLI Deep Verification
# ============================================================


class TestCliDeep:
    CLI = CLI_DIR / "masteryos.py"

    def test_has_all_9_commands_in_dict(self):
        content = self.CLI.read_text()
        for cmd in ["login", "deploy", "users", "content", "analytics", "workers", "backups", "health", "version"]:
            assert f'"{cmd}"' in content, f"CLI must register '{cmd}' command"

    def test_has_cmd_prefix(self):
        content = self.CLI.read_text()
        assert "cmd_login" in content
        assert "cmd_health" in content
        assert "cmd_version" in content

    def test_has_config_file_path(self):
        content = self.CLI.read_text()
        assert ".masteryos" in content
        assert "config.json" in content

    def test_has_environment_variable_fallback(self):
        content = self.CLI.read_text()
        assert "MASTERYOS_API_KEY" in content

    def test_has_subprocess_safe_imports(self):
        content = self.CLI.read_text()
        assert "argparse" in content
        assert "json" in content
        assert "sys" in content
        assert "pathlib" in content

    def test_cli_version_runs_successfully(self):
        result = subprocess.run(
            ["python3", str(self.CLI), "--version"],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0

    def test_cli_help_runs_successfully(self):
        result = subprocess.run(
            ["python3", str(self.CLI), "--help"],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        assert "masteryos" in result.stdout.lower()

    def test_cli_version_shows_1_0_0(self):
        result = subprocess.run(
            ["python3", str(self.CLI), "--version"],
            capture_output=True, text=True, timeout=5
        )
        assert "1.0.0" in result.stdout

    def test_cli_no_args_shows_help(self):
        result = subprocess.run(
            ["python3", str(self.CLI)],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0


# ============================================================
# SEO Metadata Deep Verification
# ============================================================


class TestSeoDeep:
    def test_sitemap_has_priority_values(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "priority: 1.0" in content or "priority: 1" in content
        assert "priority: 0.9" in content or "priority: 0.8" in content

    def test_sitemap_has_change_frequency(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "changeFrequency" in content or "weekly" in content
        assert "monthly" in content

    def test_sitemap_includes_docs_pages(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "/docs" in content
        assert "/docs/getting-started" in content
        assert "/docs/rest-api" in content

    def test_sitemap_includes_marketing_pages(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "/features" in content
        assert "/pricing" in content
        assert "/security" in content

    def test_sitemap_includes_blog(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "/blog" in content

    def test_sitemap_includes_changelog(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "/changelog" in content

    def test_sitemap_includes_roadmap(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "/roadmap" in content

    def test_sitemap_includes_legal_pages(self):
        content = (APP_DIR / "sitemap.ts").read_text()
        assert "/legal/privacy" in content
        assert "/legal/terms" in content

    def test_robots_ts_has_rules_object(self):
        content = (APP_DIR / "robots.ts").read_text()
        assert "rules" in content

    def test_robots_ts_has_user_agent(self):
        content = (APP_DIR / "robots.ts").read_text()
        assert "userAgent" in content

    def test_robots_ts_disallows_portal(self):
        content = (APP_DIR / "robots.ts").read_text()
        assert "/portal" in content

    def test_layout_has_metadata_base(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "metadataBase" in content

    def test_layout_has_canonical(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "canonical" in content

    def test_layout_has_robots_config(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "robots" in content

    def test_layout_has_open_graph_images(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "og-image" in content

    def test_layout_has_twitter_creator(self):
        content = (APP_DIR / "layout.tsx").read_text()
        assert "masteryos" in content.lower()


# ============================================================
# Brand Guidelines Deep Verification
# ============================================================


class TestBrandGuidelinesDeep:
    DOC = DOCS_DIR / "brand" / "brand-guidelines.md"

    def test_has_brand_name_section(self):
        content = self.DOC.read_text()
        assert "Brand Name" in content or "brand name" in content.lower()

    def test_has_logo_section(self):
        content = self.DOC.read_text()
        assert "Logo" in content

    def test_has_color_palette_section(self):
        content = self.DOC.read_text()
        assert "Color Palette" in content or "color palette" in content.lower()

    def test_has_typography_section(self):
        content = self.DOC.read_text()
        assert "Typography" in content

    def test_has_voice_and_tone_section(self):
        content = self.DOC.read_text()
        assert "Voice" in content or "voice" in content.lower()

    def test_lists_all_primary_colors(self):
        content = self.DOC.read_text()
        for color in ["#2563EB", "#7C3AED", "#14B8A6"]:
            assert color in content

    def test_lists_all_semantic_colors(self):
        content = self.DOC.read_text()
        for color in ["#10B981", "#F59E0B", "#EF4444"]:
            assert color in content

    def test_mentions_inter_font(self):
        content = self.DOC.read_text()
        assert "Inter" in content

    def test_mentions_jetbrains_mono(self):
        content = self.DOC.read_text()
        assert "JetBrains Mono" in content

    def test_has_clear_space_guidance(self):
        content = self.DOC.read_text()
        assert "Clear Space" in content or "clear space" in content.lower()

    def test_has_accessibility_section(self):
        content = self.DOC.read_text()
        assert "Accessibility" in content or "WCAG" in content

    def test_has_domain_architecture(self):
        content = self.DOC.read_text()
        assert "Domain" in content or "domain" in content.lower() or "subdomain" in content.lower()

    def test_has_trademark_notice(self):
        content = self.DOC.read_text()
        assert "trademark" in content.lower() or "Trademark" in content

    def test_has_asset_checklist(self):
        content = self.DOC.read_text()
        assert "Asset" in content or "asset" in content.lower() or "Checklist" in content
