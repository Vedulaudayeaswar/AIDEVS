"""Base class for the v1 ("classic builder") agents.

All model access now goes through the centralized AI service
(services.ai_client): one platform Groq key, central model configuration,
retries, rate-limit handling and usage accounting. The `api_key` parameter is
kept only for signature compatibility and is ignored.
"""
from services.ai_client import AIError, get_ai_client


class BaseAgent:
    def __init__(self, name, role, system_prompt):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.user_id = None  # set by the caller for usage accounting

    def generate_response(self, user_message, context=None, api_key=None, max_tokens=6000):
        prompt = user_message
        if context:
            prompt = f"Context from previous interactions:\n{context}\n\n{user_message}"
        try:
            return get_ai_client().complete("legacy", self.system_prompt, prompt,
                                            user_id=self.user_id, max_tokens=max_tokens, temperature=0.7).text
        except AIError as exc:
            return f"Error: {exc.user_message}"

    def extract_code(self, response):
        """Extract fenced code blocks (html/css/js/python) from a model response."""
        code_blocks = {}
        if "```html" in response:
            start = response.find("```html") + 7
            end = response.find("```", start)
            if end > start:
                code_blocks["html"] = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            if start < len(response) and response[start] == "\n":
                start += 1
            end = response.find("```", start)
            if end > start:
                content = response[start:end].strip()
                first_line, _, remainder = content.partition("\n")
                if first_line.strip().lower() in {"html", "javascript", "js", "css", "python"}:
                    content = remainder.strip()
                if "<" in content and ">" in content:
                    code_blocks["html"] = content
        elif any(tag in response for tag in ("<style>", "<script>", "<section", "<header", "<footer")):
            code_blocks["html"] = response.strip()

        for marker, key in (("```css", "css"), ("```javascript", "js"), ("```js", "js"), ("```python", "python")):
            if marker in response and key not in code_blocks:
                start = response.find(marker) + len(marker)
                end = response.find("```", start)
                if end > start:
                    code_blocks[key] = response[start:end].strip()
        return code_blocks
