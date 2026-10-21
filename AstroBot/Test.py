import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from dotenv import load_dotenv
from google import genai
from dotenv import load_dotenv

# Эта строчка автоматически ищет файл .env в папке проекта и подгружает данные в систему
load_dotenv()
# Загружаем переменные из .env файла
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Инициализируем Gemini клиент
ai_client = genai.Client(api_key=GEMINI_API_KEY)


# Описываем состояния (в каком режиме находится пользователь)
class ChatStates(StatesGroup):
    ai_mode = State()  # Режим общения с ИИ
    owner_mode = State()  # Режим отправки сообщения владельцу


# Функция для запроса к Gemini
async def ask_ai(prompt: str) -> str:
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return "Брат, нейронка сейчас перегружена или временно недоступна."


# Команда /start — выводим главное меню с кнопками
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Сбрасываем старое состояние при перезапуске
    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 ИИ-поиск (Задать вопрос)", callback_data="mode_ai")],
        [InlineKeyboardButton(text="📩 Написать лично владельцу", callback_data="mode_owner")]
    ])

    welcome_text = (
        "Йоу! Я твой личный бот-помощник.\n"
        "Выбери нужный режим работы с помощью кнопок ниже:"
    )
    await message.answer(welcome_text, reply_markup=keyboard)


# Обработка нажатия на кнопку "ИИ-поиск"
@dp.callback_query(F.data == "mode_ai")
async def set_ai_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChatStates.ai_mode)
    await callback.message.edit_text(
        "🤖 **Режим ИИ-поиска активирован!**\n"
        "Напиши свой вопрос, и я найду/сгенерирую ответ через Gemini."
    )
    await callback.answer()


# Обработка нажатия на кнопку "Написать владельцу"
@dp.callback_query(F.data == "mode_owner")
async def set_owner_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChatStates.owner_mode)
    await callback.message.edit_text(
        "📩 **Режим связи с владельцем активирован!**\n"
        "Напиши свое сообщение, и оно сразу улетит хозяину в ЛС."
    )
    await callback.answer()


# Обработка текстовых сообщений, когда включен режим ИИ
@dp.message(ChatStates.ai_mode)
async def handle_ai_chat(message: Message, state: FSMContext):
    # Игнорируем твои сообщения, если ты сам себе пишешь
    if message.from_user.id == OWNER_ID and message.chat.id == OWNER_ID:
        return

    # Отправляем сообщение пользователя в Gemini
    wait_msg = await message.answer("⏳ Ищу информацию...")
    ai_reply = await ask_ai(message.text)

    # Удаляем плашку ожидания и шлем ответ
    await wait_msg.delete()

    # Добавляем кнопку вернуться в меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Вернуться в главное меню", callback_data="back_to_menu")]
    ])
    await message.answer(ai_reply, reply_markup=keyboard)


# Обработка текстовых сообщений, когда включен режим связи с владельцем
@dp.message(ChatStates.owner_mode)
async def handle_owner_chat(message: Message, state: FSMContext):
    if message.from_user.id == OWNER_ID:
        return

    # Формируем красивое уведомление для тебя
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    notification_text = (
        f"📩 **Новое обращение от {user_info}:**\n"
        f"{message.text}"
    )

    # Отправляем тебе в ЛС
    await bot.send_message(chat_id=OWNER_ID, text=notification_text)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Вернуться в главное меню", callback_data="back_to_menu")]
    ])
    await message.answer("✅ Твое сообщение успешно отправлено владельцу!", reply_markup=keyboard)


# Кнопка возврата в главное меню из любого режима
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 ИИ-поиск (Задать вопрос)", callback_data="mode_ai")],
        [InlineKeyboardButton(text="📩 Написать лично владельцу", callback_data="mode_owner")]
    ])
    await callback.message.edit_text(
        "Главное меню. Выбери, что тебя интересует:",
        reply_markup=keyboard
    )
    await callback.answer()


async def main():
    logging.basicConfig(level=logging.INFO)
    print("Умный бот с кнопками запущен и ждет пользователей...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())