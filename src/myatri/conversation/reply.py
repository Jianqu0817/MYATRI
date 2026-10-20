"""Cheap presentation policy for the final answer; never alters tool messages."""
import re


_TIME_HEADER = re.compile(
    r"^\s*\[消息发送时间[：:]\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\s*\]\s*")


class ReplyPolicy:
    def __init__(self, options):
        self.minimum = options.get("reply_min_chars", 40)
        self.maximum = options.get("reply_max_chars", 0)
        self.max_tokens = options.get("reply_max_tokens", 512)
        if (type(self.minimum) is not int or type(self.maximum) is not int or
                type(self.max_tokens) is not int or self.minimum < 1 or self.maximum < 0 or
                self.max_tokens < 1 or (self.maximum and self.maximum < self.minimum)):
            raise ValueError("invalid reply character/token limits")

    @property
    def instruction(self):
        if not self.maximum:
            return ""
        return (f"\n本轮聊天表达：正文控制在{self.minimum}—{self.maximum}字（标点计入，空白不计）。"
                "只接住眼前这一句话，通常一小段、一两句；用自然口语，允许短句和不那么工整的节奏。"
                "不用邮件式开头、分点、总结和面面俱到的解释；不逐项复述对方的话。"
                "默认用陈述句收住，不靠反问、连续追问或‘你觉得呢/要不要/还有什么’维持聊天。"
                "只有缺少必要信息、确实无法回答时才问一个简短问题。文雅轻柔，偶尔俏皮，"
                "不用每次都撩人、卖萌或给建议。回复只含聊天正文，时间与说话人由界面显示。")

    def prepare(self, text):
        # Remove only a model-echoed leading metadata header. Quoted dates and
        # time references inside the actual answer are ordinary content.
        while _TIME_HEADER.match(text):
            text = _TIME_HEADER.sub("", text, count=1)
        text = text.strip()
        if not self.maximum:
            return text
        positions = [i for i, char in enumerate(text) if not char.isspace()]
        if len(positions) <= self.maximum:
            # Never add canned filler or make another API call to meet a floor.
            return text
        prefix = text[:positions[self.maximum - 1]]  # Room for one ellipsis.
        endings = list(re.finditer(r'[。！？!?](?:[”’」』】）)]*)', prefix))
        for ending in reversed(endings):
            candidate = prefix[:ending.end()].strip()
            if sum(not c.isspace() for c in candidate) >= self.minimum:
                return candidate
        # Prefer a clause boundary when the model ignores the length request.
        for match in reversed(list(re.finditer(r"[，,；;：:]", prefix))):
            candidate = prefix[:match.start()].rstrip()
            if sum(not c.isspace() for c in candidate) >= self.minimum:
                return candidate + "…"
        return prefix.rstrip() + "…"
