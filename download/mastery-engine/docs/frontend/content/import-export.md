# Import / Export

> Import and export content in multiple formats.

## Supported Formats

| Format | Extension | Description |
|---|---|---|
| JSON | .json | Structured data format (full fidelity) |
| Markdown | .md | Human-readable text (limited fidelity) |
| CSV | .csv | Spreadsheet format (flat data only) |
| ZIP | .zip | Complete archive (all content) |

## Import

### Process
1. Select format
2. Paste JSON data (or upload file in future)
3. Click "Preview import" to validate
4. Review warnings + errors
5. Click "Import" to execute

### Import Preview

The preview shows:
- Items to be created/updated/skipped
- Validation warnings
- Validation errors

### Validation

- JSON must be valid
- Required fields must be present
- Slugs must be unique within their scope
- References (e.g., concept_ids) must exist

## Export

### Process
1. Select format
2. Click "Export content"
3. File downloads automatically

### Export Contents

- All subjects
- All concepts
- All question templates (with versions)
- All learning objectives
- All misconceptions
- All content packs

## API Integration

- `POST /admin/content/import?format={format}` — Import data
- `POST /admin/content/export?format={format}` — Export (returns blob)
- `POST /admin/content/import/preview?format={format}` — Preview import

## Future Enhancements

- File upload (drag-and-drop)
- CSV/Markdown/ZIP format support
- Selective export (choose which items)
- Import from URL
- Scheduled exports
