# Versioning

> Template version history and comparison.

## Overview

Question templates use immutable versioning. Each edit creates a new version. Previous versions are preserved for audit and rollback.

## Version History Page

### Current Version Display
- Version number badge
- Difficulty estimate
- Prompt template (JSON)
- Correct answer generator (JSON)
- Distractor generator (JSON, if present)
- Hint tiers list
- Concept ID badges

### Version Diff
- Compares current version with previous
- Shows changes in:
  - Prompt template
  - Generators
  - Hint tiers
  - Concept mappings
  - Difficulty

## Actions

### Publish
- Makes the current version the active published version
- Previous published version is archived
- Template becomes available for question generation

### Archive
- Removes the template from active use
- Preserves all version history
- Can be unarchived

### Duplicate
- Creates a copy of the template
- New template starts in draft status
- Useful for creating variations

## Future Enhancements

- Side-by-side diff viewer
- Rollback to previous version
- Version comparison with syntax highlighting
- Version author tracking
- Change log with commit messages
