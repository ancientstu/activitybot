import time
import asyncio

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from utils import week_range_msk, month_range_msk, display_name
from keyboards import simple_kb

router = Router()


async def send_clean_ephemeral(call: CallbackQuery, config, db, kind: str, text: str, seconds: int = 30):
    """
    1) Удаляет предыдущее сообщение бота этого kind (если известно).
    2) Отправляет новое.
    3) Запоминает message_id в БД.
    4) Удаляет новое через seconds.
    """
    chat_id = call.message.chat.id
    topic_id = call.message.message_thread_id
    now = int(time.time())

    # 1) попытка удалить старое (если бот его помнит)
    old_id = await db.get_last_bot_message_id(chat_id, topic_id, kind)
    if old_id:
        try:
            await call.bot.delete_message(chat_id=chat_id, message_id=old_id)
        except TelegramBadRequest:
            pass

    # 2) отправка нового
    msg = await call.message.reply(text, reply_markup=simple_kb())
    await call.answer()

    # 3) запомнить новое
    await db.set_last_bot_message_id(chat_id, topic_id, kind, msg.message_id, now)

    # 4) автоудаление
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "rules")
async def on_rules(call: CallbackQuery, config, db):
    await send_clean_ephemeral(
        call, config, db, "rules",
        "Правила:\n"
        "1) В этой теме кидаем ссылку на пост в канале — бот создаёт задание.\n"
        "2) Поставил(а) реакцию на пост — нажми «✅ Поставил(а) реакцию».\n"
        "3) 1 человек = 1 зачёт на 1 задание.\n"
        "4) Лимит создания: 10 заданий в неделю (МСК).\n"
        "5) Задания прошлой недели не засчитываются, если началась новая.",
        seconds=30,
    )


@router.callback_query(F.data == "me")
async def on_me(call: CallbackQuery, config, db):
    now = int(time.time())

    w_start, w_end = week_range_msk(now, config.tz)
    m_start, m_end = month_range_msk(now, config.tz)

    done_week = await db.count_user_completions_in_range(call.from_user.id, w_start, w_end)
    created_week = await db.count_user_tasks_in_range(call.from_user.id, w_start, w_end)
    done_month = await db.count_user_completions_in_range(call.from_user.id, m_start, m_end)

    await send_clean_ephemeral(
        call, config, db, "me",
        f"{display_name(call.from_user)} — статистика:\n"
        f"Неделя (МСК):\n"
        f"✅ Выполнено: {done_week}\n"
        f"📝 Создано заданий: {created_week}/{config.weekly_task_limit}\n\n"
        f"Месяц (МСК):\n"
        f"✅ Выполнено: {done_month}",
        seconds=30,
    )


@router.callback_query(F.data == "top")
async def on_top(call: CallbackQuery, config, db, bot):
    now = int(time.time())
    start_ts, end_ts = week_range_msk(now, config.tz)
    top = await db.top_completions_in_range(start_ts, end_ts, limit=20)

    lines = ["🏆 Топ недели (МСК):"]
    if not top:
        lines.append("Пока пусто.")
    else:
        for i, (user_id, c) in enumerate(top, start=1):
            try:
                chat_member = await bot.get_chat_member(call.message.chat.id, user_id)
                name = display_name(chat_member.user)
            except Exception:
                name = str(user_id)
            lines.append(f"{i}. {name} — {c}")

    await send_clean_ephemeral(call, config, db, "top", "\n".join(lines), seconds=30)


@router.callback_query(F.data == "month_top")
async def on_month_top(call: CallbackQuery, config, db, bot):
    now = int(time.time())
    start_ts, end_ts = month_range_msk(now, config.tz)
    top = await db.top_completions_in_range(start_ts, end_ts, limit=20)

    lines = ["🏅 Топ месяца (МСК):"]
    if not top:
        lines.append("Пока пусто.")
    else:
        for i, (user_id, c) in enumerate(top, start=1):
            try:
                chat_member = await bot.get_chat_member(call.message.chat.id, user_id)
                name = display_name(chat_member.user)
            except Exception:
                name = str(user_id)
            lines.append(f"{i}. {name} — {c}")

    await send_clean_ephemeral(call, config, db, "month_top", "\n".join(lines), seconds=30)