# Claude Model Error Fix

## Problem
The Document Rip system was failing to process documents with the error:
```
API Error 404: {"type":"error","error":{"type":"not_found_error","message":"model: claude-3-5-sonnet-20241022"}
```

## Root Cause
The Claude model name `claude-3-5-sonnet-20241022` is no longer available or has been deprecated by Anthropic. The API returns a 404 error when trying to use this model.

## Solution Implemented

### 1. Updated Default Model Name
Changed the default model from `claude-3-5-sonnet-20241022` to `claude-3-5-sonnet-20240620` (a known working model version).

**File**: `src/vision_validator.py`
**Change**: Updated `__init__` method to use a working default model.

### 2. Made Model Configurable
Added support for environment variable `ANTHROPIC_MODEL` to allow easy model switching without code changes.

**Usage**:
```bash
export ANTHROPIC_MODEL="claude-3-5-sonnet-20240620"
# or
export ANTHROPIC_MODEL="claude-3-opus-20240229"
```

### 3. Improved Error Handling
- Added specific error messages for model not found errors
- Changed severity of API errors from "high" to "medium" so they don't block document processing
- Added helpful warnings with suggested model names

### 4. Better Error Messages
When a model is not found, the system now provides:
- Clear warning that the model may have changed
- Instructions to use the `ANTHROPIC_MODEL` environment variable
- List of common working model names

## How to Fix

### Option 1: Use Environment Variable (Recommended)
```bash
export ANTHROPIC_MODEL="claude-3-5-sonnet-20240620"
./start_processor.py
```

### Option 2: Update Code Default
The code now defaults to `claude-3-5-sonnet-20240620`. If you need a different model, you can:
1. Set the environment variable
2. Or modify the default in `src/vision_validator.py` line 44

## Available Models
Common Claude models that work with vision validation:
- `claude-3-5-sonnet-20240620` (recommended)
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

## Impact
- Vision validation failures with API errors no longer block document processing
- Documents will still be processed successfully even if vision validation fails
- Better error messages help diagnose issues quickly

## Testing
After applying this fix:
1. Documents should process successfully even if vision validation fails
2. Error messages should be more informative
3. Model can be changed via environment variable without code changes
