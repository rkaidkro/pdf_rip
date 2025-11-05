# Setting Up OpenAI API Key

To use LLM vision for better text extraction (especially for scanned PDFs):

1. Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_actual_openai_api_key_here
   ```

2. The pipeline will automatically:
   - Use LLM vision for ALL PDFs (not just scanned)
   - Verify OCR results with LLM if OCR is used
   - Run a final LLM verification pass to ensure completeness

3. The `.env` file is already in `.gitignore` so your API key won't be committed.

Once you add the API key, the pipeline will automatically use LLM vision for all processing.
