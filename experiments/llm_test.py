import os
import json
import requests

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY is not set.")

url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

abstract = """
This study investigates whether AI-assisted feedback can improve
university students' academic writing performance. Eighty students
were randomly assigned to either an AI-feedback group or a traditional
feedback group. Both groups completed a writing task before and after
a four-week intervention. The AI-feedback group showed a larger
improvement in writing scores than the traditional feedback group.
The study was conducted at a single university and the sample size
was relatively small.
"""

payload = {
    "model": "z-ai/glm-5.2:free",
    "messages": [
        {
            "role": "system",
            "content": (
                "You extract structured information from academic abstracts. "
                "Use only information explicitly supported by the provided abstract. "
                "Do not infer or invent missing information. "
                "If information for a field is not available in the abstract, "
                "return exactly 'Not available in the source'."
            )
        },
        {
            "role": "user",
            "content": f"Analyze the following academic abstract:\n\n{abstract}"
        }
    ],
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "paper_analysis",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "research_problem": {
                        "type": "string"
                    },
                    "methodology": {
                        "type": "string"
                    },
                    "key_findings": {
                        "type": "string"
                    },
                    "limitations": {
                        "type": "string"
                    }
                },
                "required": [
                    "research_problem",
                    "methodology",
                    "key_findings",
                    "limitations"
                ],
                "additionalProperties": False
            }
        }
    },
    "provider": {
        "require_parameters": True
    }
}

try:
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120
    )
except requests.RequestException as error:
    print("Request failed:")
    print(error)
    raise SystemExit(1)

print("Status code:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit(1)

data = response.json()

print("Model:", data.get("model"))
print("Provider:", data.get("provider"))

content = data["choices"][0]["message"]["content"]

print("\nRaw content:")
print(content)

try:
    result = json.loads(content)
except json.JSONDecodeError as error:
    print("\nModel did not return valid JSON.")
    print(error)
    raise SystemExit(1)

required_fields = {
    "research_problem",
    "methodology",
    "key_findings",
    "limitations"
}

if set(result.keys()) != required_fields:
    print("\nReturned JSON does not match expected fields.")
    print("Expected:", required_fields)
    print("Received:", set(result.keys()))
    raise SystemExit(1)

print("\nParsed result:")
print(json.dumps(result, indent=2, ensure_ascii=False))

print("\nLLM feasibility test PASSED.")