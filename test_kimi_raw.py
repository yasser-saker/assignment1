import sys
sys.path.insert(0, '.')
from src.extraction.llm_client import LLMClient

client = LLMClient(model='kimi-k2.5', provider='kimi')

# Test with a very specific small prompt
prompt = """Extract line items from this construction text:
Install 5 recessed light fixtures, model LFPR-12-835-UNV-EB81-U, in corridor.
Install 3 duplex receptacles on wall.
Paint walls with Sherwin Williams Wordly Gray #SW7043, Eggshell finish.

Return ONLY a JSON object with key "line_items" containing an array. Each item must have: description, trade, quantity, unit, confidence."""

# Call API directly to see raw response
api_client = client._get_client()
response = api_client.chat.completions.create(
    model='kimi-k2.5',
    messages=[
        {'role': 'system', 'content': 'You are a construction estimator. Return JSON only.'},
        {'role': 'user', 'content': prompt}
    ],
    temperature=1.0,
    max_tokens=2000
)
content = response.choices[0].message.content
print(f'Raw response length: {len(content)}')
print(f'Raw response preview: {content[:1000]!r}')
