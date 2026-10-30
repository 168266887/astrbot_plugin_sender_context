"""对话者身份注入：把当前发言人的昵称/账号/场景作为「临时用户内容」注入。

为什么不直接拼 system prompt：
    system prompt 是供应商 prompt 缓存的前缀，每次请求都往里塞会变的内容
    （昵称、账号、群号）会让缓存命中率归零，成本和时间都会上升。
    所以这里改用 req.extra_user_content_parts，并用 mark_as_temp() 标记，
    表示「只给本次请求的模型看，不写进会话历史」，缓存前缀保持稳定。
"""
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register
from astrbot.core.agent.message import TextPart


@register("sender_context", "dsh", "把发言人 QQ/昵称/场景作为临时内容提供给模型", "0.1.1")
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

        text = (
            "（系统附注，非用户发言）当前对话者信息："
            + " | ".join(parts)
            + "。判断该用哪副人格/怎么称呼时以此为准，不要凭感觉猜，也不要向对方复述这条附注。"
        )

        try:
            req.extra_user_content_parts.append(TextPart(text=text).mark_as_temp())
        except Exception as exc:
            logger.warning(f"[sender_context] 注入失败: {exc}")
            return

        if self.config.get("debug_mode", False):
            logger.info(f"[sender_context] 已注入: {text}")
