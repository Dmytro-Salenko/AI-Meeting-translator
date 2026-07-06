import json
import httpx
from app.core.config import settings
from app.core.interfaces.summary import BaseSummaryProvider, MeetingSummarySchema


class OpenRouterSummaryProvider(BaseSummaryProvider):
    """
    Implementation of BaseSummaryProvider using OpenRouter API with Structured outputs / strict JSON validation.
    """

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def generate_summary(self, full_transcript: str) -> MeetingSummarySchema:
        if not full_transcript.strip():
            return MeetingSummarySchema(
                brief_content="Встреча пуста.",
                key_decisions=[],
                action_items=[],
                open_questions=[]
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/dimasalenko/ai-meeting-translator",
            "X-Title": "AI Meeting Translator"
        }

        # System prompt with strict JSON schema instructions
        system_prompt = (
            "You are an expert secretary assistant. Analyze the transcript of the meeting and generate a structured summary. "
            "You must return ONLY a JSON object that strictly adheres to the following JSON schema:\n"
            "{\n"
            "  \"brief_content\": \"string (2-3 paragraphs describing the general context and essence in Russian)\",\n"
            "  \"key_decisions\": [\"string (bulleted list of agreements in Russian)\"],\n"
            "  \"action_items\": [\n"
            "    { \"assignee\": \"string (name of person responsible, or null if unknown)\", \"task\": \"string (task description in Russian)\" }\n"
            "  ],\n"
            "  \"open_questions\": [\"string (unresolved issues/questions in Russian)\"]\n"
            "}\n"
            "Do not include any markdown styling like ```json or any other text before/after the JSON content."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcript:\n{full_transcript}"}
            ],
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

            result = response.json()
            raw_content = result["choices"][0]["message"]["content"].strip()
            
            # Clean up potential markdown formatting if LLM failed to follow response_format strictly
            if raw_content.startswith("```"):
                lines = raw_content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_content = "\n".join(lines).strip()

            # Parse and validate using Pydantic
            parsed_json = json.loads(raw_content)
            return MeetingSummarySchema.model_validate(parsed_json)
class MockSummaryProvider(BaseSummaryProvider):
    """
    Mock implementation of BaseSummaryProvider.
    """
    async def generate_summary(self, full_transcript: str) -> MeetingSummarySchema:
        return MeetingSummarySchema(
            brief_content="Mock Summary: This is an automatically generated brief summary of the conversation.",
            key_decisions=["Decided to proceed with Step 4 implementation.", "Agreed on API contracts."],
            action_items=[
                {"assignee": "Dmitry", "task": "Write Flutter application."},
                {"assignee": "AI Agent", "task": "Validate database integrity."}
            ],
            open_questions=["How to handle large files > 1GB?"]
        )
