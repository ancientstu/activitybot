from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "/debug")
async def debug_ids(message: Message):
    await message.reply(
        "DEBUG\n"
        f"chat_id: {message.chat.id}\n"
        f"message_thread_id: {message.message_thread_id}\n"
        f"chat_type: {message.chat.type}\n"
    )