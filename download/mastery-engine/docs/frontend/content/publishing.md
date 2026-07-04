# Publishing Workflow

> Draft → Review → Approve → Publish → Archive

## Workflow States

```
Draft → In Review → Published → Archived
          ↓
       Rejected
```

## Subject Publishing

### From Subject Detail Page
1. Subject must be in "draft" status
2. Click "Publish subject" button
3. Backend transitions subject to "published"
4. Subject becomes available for learner enrollment

## Template Publishing

### From Template Detail Page
1. Template must have a current version
2. Click "Publish" button
3. Backend transitions template to "published"
4. Template becomes available for question generation in study sessions

## Publishing Queue

The content dashboard shows a publishing queue with:
- Item name
- Type (subject, template, content pack)
- Readiness status (Ready / Issues)
- Validation issues count

### Validation Checks
- Concept coverage: Template must be linked to at least one concept
- Explanation coverage: Template should have at least a "correct" explanation variant
- Parameter schema validity: JSON must be parseable
- Prompt template: Must not be empty

## Publishing Checklist

Before publishing, ensure:
- [ ] Template has a valid prompt
- [ ] Correct answer generator produces valid output
- [ ] At least one explanation variant exists
- [ ] Template is linked to concepts
- [ ] Live preview generates correctly with multiple seeds
- [ ] Difficulty estimate is accurate
