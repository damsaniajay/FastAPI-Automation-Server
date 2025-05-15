from typing import Dict, Any
from datetime import datetime
import logging

# Initialize logger
logger = logging.getLogger(__name__)

def generate_prompt(test_case: Dict[str, Any]) -> str:
    """
    Generate a markdown-formatted prompt for test automation tailored for OpenAI Operator.

    Args:
        test_case: Test case dict containing test case details

    Returns:
        Formatted prompt string
    """
    try:
        # Extract test case details
        title = test_case.get("summary", "Untitled Test Case")
        key = test_case.get("key", "Unknown-Key")
        steps = test_case.get("test_steps", [])

        # Start building the prompt
        prompt = f"""You are an AI test operator. Automate the following test case by performing each step.

If any intermediate UI state, confirmation, or popup appears, handle it automatically without asking for input.

After executing all steps, return only a JSON array with objects containing:
- test_step: action performed (do not include markdown formatting like ** in this value)
- log_or_error: success message or error
- result: "Pass" or "Fail"
- timestamp: current time in ISO 8601 format

IMPORTANT: Ensure your JSON response is valid and parseable. Do not include any markdown formatting characters in the JSON values.

Test Case: **{title}**  
Test Case Key: **{key}**

Steps:"""

        # Add each test step to the prompt
        for i, step in enumerate(steps, 1):
            action = step.get("test_step", "No action provided")
            expected = step.get("expected_output", "No expected result provided")
            prompt += f"\n{i}. **{action}**\n   Expected Result: {expected}"

        # Final instruction with explicit warning about formatting
        prompt += """

IMPORTANT FORMATTING INSTRUCTIONS:
1. Return ONLY the final JSON array with no other text
2. Do NOT include markdown formatting like ** in your JSON values
3. Ensure all JSON values are properly escaped
4. Example format:
[
  {
    "test_step": "Launch browser and go to https://example.com",
    "log_or_error": "Homepage loaded successfully",
    "result": "Pass",
    "timestamp": "2023-05-01T10:15:00Z"
  }
]
"""

        return prompt

    except Exception as e:
        logger.error(f"Error generating prompt: {str(e)}")
        return "Error generating test automation prompt."