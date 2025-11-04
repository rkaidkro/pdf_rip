# Output Structure Changes

## Summary

Updated the output folder structure to provide a cleaner, more intuitive organization where markdown files match the input file names.

## Changes Made

### 1. Fixed File Movement Issue
**Problem**: The folder processor was trying to move files that had already been moved by the file system watcher, causing errors.

**Solution**: Added existence check before attempting to move files:
```python
# Check if file still exists before trying to move it
if not file_path.exists():
    logger.warning(f"File {file_path} no longer exists, skipping move")
    return
```

### 2. Updated Output Structure
**Problem**: Markdown files were buried in subfolders with generic names like `document.md`.

**Solution**: Changed to flat structure with markdown files matching input names:

#### Before:
```
markdown/
└── document_name/
    ├── document.md          # Generic name
    ├── provenance.jsonl
    └── run_report.json
```

#### After:
```
markdown/
└── document_name/           # All files in one folder
    ├── document_name.md     # Matches input filename
    ├── provenance.jsonl
    └── run_report.json
```

### 3. Implementation Details

**File**: `src/processor.py` - `_generate_output()` method
- Markdown files are now saved directly in the main output directory
- Filename matches the input document name (e.g., `input.pdf` → `input.md`)
- Additional files (provenance, reports) are stored in a subfolder
- Maintains backward compatibility for bytes input

**File**: `src/folder_processor.py` - `_move_to_processed()` method
- Added file existence check to prevent movement errors
- Improved error handling and logging

## Benefits

1. **Easier Access**: Markdown files are directly accessible in the main output folder
2. **Clear Naming**: Output files match input file names for easy identification
3. **Organized Structure**: Additional metadata is kept separate but organized
4. **Reduced Errors**: File movement issues are resolved
5. **Better UX**: Users can quickly find their converted documents

## Example

**Input**: `input/cover_letter.docx`

**Output Structure**:
```
markdown/
└── cover_letter/            # All files in one folder
    ├── cover_letter.md      # Main markdown file (matches input name)
    ├── provenance.jsonl     # Element-level provenance
    └── run_report.json      # Quality metrics and metadata
```

## Testing

✅ **Verified working** with test document:
- Input: `another_test.docx`
- Output: `markdown/another_test.md` (2119 bytes of content)
- Additional files in `markdown/another_test/`

The new structure provides a much cleaner and more intuitive organization while maintaining all the detailed metadata and quality information.
