import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from keyboards import task_kb, simple_kb
from utils import (
    extract_first_tme_url,
    parse_post_key,
    week_range_msk,
    display_name,
    is_same_week_msk,
)

router = Router()


def allowed_place(message: Message, chat_id: int, topic_id: int) -> bool:
    return (message.chat.id == chat_id) and (message.message_thread_id == topic_id)


def allowed_place_cb(call: CallbackQuery, chat_id: int, topic_id: int) -> bool:
    msg = call.message
    return msg and (msg.chat.id == chat_id) and (msg.message_thread_id == topic_id)


@router.message(F.text)
async def on_message_with_link(message: Message, config, db):
    if not allowed_place(message, config.chat_id, config.topic_id):
        return

    url = extract_first_tme_url(message.text)
    if not url:
        return

    post_key = parse_post_key(url)
    if not post_key:
        await message.reply(
            "Не понял ссылку. Нужна ссылка вида t.me/<канал>/<id> или t.me/c/<id>/<id>.",
            reply_markup=simple_kb(),
        )
        return

    now = int(time.time())

    if await db.is_banned(message.from_user.id, now):
        await message.reply(
            "Тебе сейчас нельзя отмечать выполнения/создавать задания.",
            reply_markup=simple_kb(),
        )
        return

    start_ts, end_ts = week_range_msk(now, config.tz)
    created_count = await db.count_user_tasks_in_range(message.from_user.id, start_ts, end_ts)
    if created_count >= config.weekly_task_limit:
        await message.reply(
            f"Лимит: {config.weekly_task_limit} заданий в неделю (МСК).\n"
            f"На этой неделе у тебя уже {created_count}/{config.weekly_task_limit}.",
            reply_markup=simple_kb(),
        )
        return

    existing = await db.get_task_by_post_key(post_key)
    if existing and existing["active"]:
        await message.reply(
            f"Такое задание уже есть: #{existing['id']}.",
            reply_markup=task_kb(existing["id"]),
        )
        return

    task_id = await db.create_task(
        chat_id=message.chat.id,
        topic_id=message.message_thread_id,
        created_by=message.from_user.id,
        post_url=url,
        post_key=post_key,
        created_at=now,
    )

    text = (
        f"Задание #{task_id}\n"
        f"Ссылка: {url}\n"
        f"Создал: {display_name(message.from_user)}\n"
        f"Выполнили: 0"
    )
    card = await message.reply(text, reply_markup=task_kb(task_id))
    await db.set_task_card_message_id(task_id, card.message_id)


@router.callback_query(F.data.startswith("done:"))
async def on_done(call: CallbackQuery, config, db):
    if not allowed_place_cb(call, config.chat_id, config.topic_id):
        await call.answer("Кнопки работают только в нужной теме.", show_alert=True)
        return

    task_id = int(call.data.split(":")[1])
    now = int(time.time())

    if await db.is_banned(call.from_user.id, now):
        await call.answer("Тебе сейчас нельзя участвовать.", show_alert=True)
        return

    task = await db.get_task(task_id)
    if not task or not task["active"]:
        await call.answer("Задание не найдено или отключено.", show_alert=True)
        return

    # В зачёт не идут задания прошлой недели
    if not is_same_week_msk(task["created_at"], now, config.tz):
        await call.answer("Это задание из прошлой недели. В зачёт не идёт.", show_alert=True)
        return

    inserted = await db.add_completion(task_id, call.from_user.id, now)
    count = await db.count_completions(task_id)

    try:
        await call.message.edit_text(
            f"Задание #{task_id}\n"
            f"Ссылка: {task['post_url']}\n"
            f"Выполнили: {count}",
            reply_markup=task_kb(task_id),
        )
    except TelegramBadRequest:
        pass

    await call.answer("Засчитано." if inserted else "Уже было засчитано.", show_alert=False)


@router.callback_query(F.data.startswith("undo:"))
async def on_undo(call: CallbackQuery, config, db):
    if not allowed_place_cb(call, config.chat_id, config.topic_id):
        await call.answer("Кнопки работают только в нужной теме.", show_alert=True)
        return

    task_id = int(call.data.split(":")[1])
    task = await db.get_task(task_id)
    if not task or not task["active"]:
        await call.answer("Задание не найдено или отключено.", show_alert=True)
        return

    removed = await db.remove_completion(task_id, call.from_user.id)
    count = await db.count_completions(task_id)

    try:
        await call.message.edit_text(
            f"Задание #{task_id}\n"
            f"Ссылка: {task['post_url']}\n"
            f"Выполнили: {count}",
            reply_markup=task_kb(task_id),
        )
    except TelegramBadRequest:
        pass

    await call.answer("Отменено." if removed else "У тебя не было зачёта.", show_alert=False)