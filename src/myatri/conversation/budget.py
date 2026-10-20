import json
import math

from myatri.providers import BudgetExceeded


class TokenBudget:
    """Conservative UTF-8-byte ceiling until actual provider usage calibrates it."""
    def __init__(self, limit=16000, output_reserve=1024, safety=512):
        self.limit, self.output_reserve, self.safety = limit, output_reserve, safety
        self.ratio = 1.0

    def estimate(self, messages, tools=None):
        payload = {"messages": messages, "tools": tools or []}
        return math.ceil(len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) * self.ratio) + 64

    def fits(self, messages, tools=None):
        return self.estimate(messages, tools) + self.output_reserve + self.safety <= self.limit

    def require(self, messages, tools=None):
        if not self.fits(messages, tools):
            raise BudgetExceeded("fixed context/request exceeds budget; reduce recall or increase configured context budget")

    def calibrate(self, messages, usage, tools=None):
        actual = usage.get("prompt_tokens")
        raw = len(json.dumps({"messages": messages, "tools": tools or []}, ensure_ascii=False).encode("utf-8")) + 64
        if actual:
            # Keep margin; never silently use the English chars/4 rule for Chinese.
            self.ratio = max(self.ratio, actual / max(1, raw) * 1.2)
