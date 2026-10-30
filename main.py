"""把当前发言人身份注入 system prompt，供"按人切换人格"的设定判断。"""
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register


@register("sender_context", "dsh", "把发言人 QQ/昵称/场景写进 prompt", "0.1.0")
class SenderContext(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config or {}

    @filter.on_llm_request()
    async def inject_sender(self, event: AstrMessageEvent, req: ProviderRequest):
        if not self.config.get("enabled", True):
            return
        try:
            sender_id = str(event.get_sender_id() or "")
            sender_name = str(event.get_sender_name() or "")
            group_id = str(event.get_group_id() or "")
            platform = str(event.get_platform_name() or "")
        except Exception as exc:
            logger.debug(f"[sender_context] 取事件信息失败: {exc}")
            return

        parts = []
        if sender_name:
            parts.append(f"昵称={sender_name}")
        if sender_id:
            parts.append(f"账号={sender_id}")
        if group_id and self.config.get("include_group_id", True):
            parts.append(f"场景=群聊({group_id})")
        else:
            parts.append("场景=私聊")
        if platform:
            parts.append(f"平台={platform}")
        if not parts:
            return

        block = (
            "\n\n# 当前对话者（判断该用哪副人格时以此为准，不要凭感觉猜）\n"
            "- " + " | ".join(parts) + "\n"
        )
        req.system_prompt = (req.system_prompt or "") + block
