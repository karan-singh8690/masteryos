"""Template Engine — deterministic placeholder expansion.

Supports {{variable}} placeholders and renders them with generated values.
No runtime LLM. Pure deterministic expansion.

Supported placeholders:
    {{variable_name}}  — replaced by the variable's value
    {{list}}           — renders a list literal
    {{dictionary}}     — renders a dict literal
    {{number}}         — renders a number
    {{operator}}       — renders a Python operator
    {{datatype}}       — renders a Python type name
    {{function}}       — renders a function call
    {{class}}          — renders a class name

Conditional rendering:
    {{#if variable}}...{{/if}}  — include content only if variable is truthy
    {{#each list}}...{{/each}}  — iterate over a list
"""

from __future__ import annotations

import re
from typing import Any


class TemplateEngine:
    """Renders templates by expanding {{variable}} placeholders.

    Usage:
        engine = TemplateEngine()
        rendered = engine.render("What is the time complexity of {{operation}} on a {{structure}}?",
                                  {"operation": "lookup", "structure": "dict"})
        # → "What is the time complexity of lookup on a dict?"
    """

    # Pattern for {{variable}} placeholders
    _PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")
    # Pattern for {{#if variable}}...{{/if}}
    _IF_PATTERN = re.compile(r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}", re.DOTALL)
    # Pattern for {{#each list}}...{{/each}}
    _EACH_PATTERN = re.compile(r"\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}", re.DOTALL)

    def render(self, template: str, variables: dict[str, Any]) -> str:
        """Render a template by expanding all placeholders.

        Args:
            template: The template string with {{variable}} placeholders.
            variables: The variable values to substitute.

        Returns:
            The rendered string with all placeholders replaced.
        """
        result = template

        # Handle {{#each list}}...{{/each}} blocks
        result = self._render_each_blocks(result, variables)

        # Handle {{#if variable}}...{{/if}} blocks
        result = self._render_if_blocks(result, variables)

        # Handle simple {{variable}} placeholders
        result = self._render_placeholders(result, variables)

        return result

    def render_dict(self, template: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
        """Render all string values in a dict.

        Recursively processes nested dicts and lists.
        """
        return self._render_recursive(template, variables)

    def _render_recursive(self, obj: Any, variables: dict[str, Any]) -> Any:
        if isinstance(obj, str):
            return self.render(obj, variables)
        if isinstance(obj, dict):
            return {k: self._render_recursive(v, variables) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._render_recursive(item, variables) for item in obj]
        return obj

    def _render_placeholders(self, text: str, variables: dict[str, Any]) -> str:
        """Replace {{variable}} placeholders with their values."""
        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            if var_name in variables:
                value = variables[var_name]
                return self._format_value(value)
            return match.group(0)  # Leave unresolvable placeholders as-is

        return self._PLACEHOLDER_PATTERN.sub(replace, text)

    def _render_if_blocks(self, text: str, variables: dict[str, Any]) -> str:
        """Process {{#if variable}}...{{/if}} blocks."""
        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            content = match.group(2)
            if var_name in variables and variables[var_name]:
                return content
            return ""

        return self._IF_PATTERN.sub(replace, text)

    def _render_each_blocks(self, text: str, variables: dict[str, Any]) -> str:
        """Process {{#each list}}...{{/each}} blocks."""
        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            template = match.group(2)
            if var_name not in variables:
                return ""
            items = variables[var_name]
            if not isinstance(items, (list, tuple)):
                return ""
            rendered_items = []
            for i, item in enumerate(items):
                item_vars = {**variables, "item": item, "index": i}
                rendered_items.append(self._render_placeholders(template, item_vars))
            return "".join(rendered_items)

        return self._EACH_PATTERN.sub(replace, text)

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format a value for rendering."""
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, (list, tuple)):
            return str(list(value))
        if isinstance(value, dict):
            return str(value)
        return str(value)
