import asyncio
from aiogram import Router
from aiogram.types import ChatMemberUpdated
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

router = Router()


@router.chat_member()
async def on_user_join(event: ChatMemberUpdated, config):
    # работаем только в нужной группе
    if event.chat.id != config.chat_id:
        return

    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    # Нас интересует именно ВХОД в группу
    if old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED) and \
       new_status == ChatMemberStatus.MEMBER:

        user = event.new_chat_member.user

        text = (
            f"👋 Добро пожаловать, {user.mention_html()}!\n\n"
            "Рады видеть тебя на нашем чудесном корабле.\n"
            "Обязательно загляни в тему Правила и Знакомства ☺"
        )

        msg = await event.bot.send_message(
            chat_id=config.chat_id,
            message_thread_id=config.welcome_topic_id,
            text=text,
        )

        # автоудаление приветствия
        await asyncio.sleep(config.welcome_delete_after)
        try:
            await msg.delete()
        except TelegramBadRequest:
            pass