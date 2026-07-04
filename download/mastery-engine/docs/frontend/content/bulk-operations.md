# Bulk Operations

> Perform actions on multiple content items at once.

## Supported Actions

| Action | Description |
|---|---|
| Publish | Publish multiple templates/subjects |
| Archive | Archive multiple items |
| Delete | Delete multiple items |
| Export | Export selected items |
| Tag | Add tags to multiple items |
| Move | Move items between subjects |

## API Integration

- `POST /admin/content/bulk` — Execute bulk operation
  - Request: `{ action, items: [{ type, id }], options? }`
  - Response: `{ success, affected_count, errors: [{ id, error }] }`

## Usage

The bulk operation API accepts:
- `action`: One of 'publish', 'archive', 'delete', 'export', 'tag', 'move'
- `items`: Array of `{ type, id }` objects
- `options`: Optional configuration (e.g., tag names, target subject)

## Error Handling

The API returns per-item errors:
```json
{
  "success": true,
  "affected_count": 8,
  "errors": [
    { "id": "tpl-3", "error": "Cannot publish: missing explanation" }
  ]
}
```

The UI shows a summary of successes and failures after the operation completes.

## Future Enhancements

- Select-all checkbox on list pages
- Bulk action toolbar
- Confirmation dialog for destructive actions
- Progress indicator for large operations
