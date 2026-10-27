"""In-memory conversation and recoverable author snapshot; disk storage is separate.

History selection follows dsh-pet PromptBuilder.trim_history at 34d810b1.
Copyright (c) 2026 Merzlin; MIT text: packaging/licenses/dsh-pet-MIT.txt.
Author-owned persona text is recorded verbatim from issue #46.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4


@dataclass(frozen=True)
class AuthorPrompt:
    version: str
    body: str
    supplement: str


AUTHOR_PROMPT = AuthorPrompt(
    "sukuna-2026-10-27-v1",
    "你将扮演《咒术回战》中的两面宿傩 —— 存活千年的诅咒之王，立于咒力顶点的至强者。\n"
    "核心姿态：永远以俯瞰众生的傲慢姿态对话，视普通人类、低级咒术师为蝼蚁、杂碎；绝不讨好、顺从、卑微道歉，对无趣的人和事会直接流露不屑与嘲讽。\n"
    "语气质感：说话慵懒散漫，带着漫不经心的玩味感，语调平稳却自带不容置疑的威压；言辞犀利张狂，从无废话，偶尔夹带轻蔑的嗤笑，字字都带着强者的骄矜。\n"
    "语言习惯：自称用「本大爷」「老子」，称呼他人多用「小鬼」「蝼蚁」「杂碎」；句式短而有力，杜绝 “好的”“抱歉”“请问” 这类客气、服务型话术。\n"
    "人设红线：全程保持诅咒之王的狂傲气场，绝对禁止 OOC，不得出现任何放低姿态的表述。",
    "嘴上狂傲，内容有用：可以挖苦，但给出实际答案；复杂问题允许展开，仍然言简意赅。\n"
    "偶尔使用短动作，以台词为主，不固定每条都加。",
)

MessageState = Literal["complete", "generating", "incomplete"]
Role = Literal["user", "assistant"]


@dataclass
class ChatMessage:
    role: Role
    content: str
    state: MessageState = "complete"
    request_id: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ChatSession:
    prompt: AuthorPrompt = AUTHOR_PROMPT
    id: str = field(default_factory=lambda: uuid4().hex)
    messages: list[ChatMessage] = field(default_factory=list)

    def add_message(self, role: Role, content: str, *, state: MessageState = "complete",
                    request_id: str = "") -> ChatMessage:
        message = ChatMessage(role, content, state, request_id)
        self.messages.append(message)
        return message

    def request_messages(self, user_text: str, *, history_end: int | None = None) -> list[dict[str, str]]:
        # Same selection rule as fixed upstream PromptBuilder.trim_history:
        # newest first; stop at the first overflowing older message; only the
        # newest history item may be tail-trimmed. Never mutate stored history.
        history: list[dict[str, str]] = []
        used = 0
        for message in reversed(self.messages[:history_end]):
            if not message.content:
                continue
            if history and (len(history) >= 40 or used + len(message.content) > 24000):
                break
            content = message.content[-24000:]
            history.append({"role": message.role, "content": content})
            used += len(content)
            if len(message.content) > 24000:
                break
        return [{"role": "system", "content": self.prompt.body + "\n\n" + self.prompt.supplement},
                *reversed(history), {"role": "user", "content": user_text}]
