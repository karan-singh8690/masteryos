#!/usr/bin/env python3
"""Extract text from the AI Agent System Prompt PDF."""

from pypdf import PdfReader
import sys

pdf_path = "/home/z/my-project/upload/AI Agent System Prompt.pdf"
output_path = "/home/z/my-project/upload/extracted_prompts.txt"

reader = PdfReader(pdf_path)
print(f"Total pages: {len(reader.pages)}")

with open(output_path, "w", encoding="utf-8") as f:
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        # Remove surrogate characters that can't be encoded
        text = text.encode('utf-8', 'replace').decode('utf-8')
        f.write(f"\n{'='*80}\nPAGE {i+1}\n{'='*80}\n")
        f.write(text)
        f.write("\n")

print(f"Extracted to: {output_path}")

# Print first 3000 chars to preview
with open(output_path, "r", encoding="utf-8") as f:
    content = f.read()
print(f"Total characters: {len(content)}")
print("\n=== FIRST 3000 CHARS ===")
print(content[:3000])
