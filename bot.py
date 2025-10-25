import asyncio
import os
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv


# =======================
#  НАСТРОЙКИ
# =======================
# 👉 ВСТАВЬ СВОЙ ТОКЕН
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# файл для хранения пользователей, кому уже показывали приветствие
SEEN_FILE = Path("seen_users.json")


# =======================
#  УТИЛИТЫ
# =======================
def load_seen_users() -> set[int]:
    if SEEN_FILE.exists():
        try:
            data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
            return set(map(int, data))
        except Exception:
            return set()
    return set()

def save_seen_users(users: set[int]) -> None:
    try:
        SEEN_FILE.write_text(json.dumps(list(users)), encoding="utf-8")
    except Exception:
        pass

def to_float(text: str) -> float:
    return float(text.strip().replace(" ", "").replace(",", "."))

def fmt(x: float, digits: int = 4) -> str:
    s = f"{x:.{digits}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


# =======================
#  КОНСТАНТЫ
# =======================
WELCOME_MSG = (
   "👋 Привет! Ты в официальном боте сообщества <b>Arbitrage Room | by M&N</b>.\n\n"
    "⚙️ Этот бот — быстрый калькулятор прибыли. Он ничего не сохраняет и создан "
    "исключительно для участников нашего комьюнити.\n\n"
    "🔒 Использование: бот является внутренним инструментом и не предназначен для "
    "распространения или использования вне Arbitrage Room. Передавать доступ, копировать "
    "или публиковать его запрещено.\n\n"
    "👤 Автор бота: <b>@voskry</b>.\n"
    "💬 Если есть идеи, как улучшить бота или что-то добавить — не стесняйся предложить "
    "в чате или написать лично. Любая обратная связь приветствуется 🙌"
)


# =======================
#  FSM
# =======================
class CalcStates(StatesGroup):
    waiting_for_eur = State()
    waiting_for_course = State()
    waiting_for_telegram_course = State()


# =======================
#  ИНИЦИАЛИЗАЦИЯ
# =======================
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN)
SEEN_USERS: set[int] = load_seen_users()


# =======================
#  ХЕНДЛЕРЫ
# =======================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    if uid not in SEEN_USERS:
        SEEN_USERS.add(uid)
        save_seen_users(SEEN_USERS)
        await message.answer(WELCOME_MSG, parse_mode=ParseMode.HTML)

    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Посчитать прибыль", callback_data="calc_profit")
    kb.adjust(1)
    await message.answer(
        "Привет! Введу сумму, курс и покажу прибыль.\n\nНажми кнопку 👇",
        reply_markup=kb.as_markup()
    )

@dp.message(Command("chatid"))
async def get_chat_id(message: types.Message):
    await message.answer(f"🆔 Chat ID: <code>{message.chat.id}</code>", parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "calc_profit")
async def ask_eur(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("💶 Введи сумму в EUR:")
    await state.set_state(CalcStates.waiting_for_eur)

@dp.message(CalcStates.waiting_for_eur)
async def eur_input(message: types.Message, state: FSMContext):
    try:
        eur = to_float(message.text)
        if eur <= 0:
            raise ValueError
        await state.update_data(eur=eur)
        await message.answer("💱 Введи курс продажи:")
        await state.set_state(CalcStates.waiting_for_course)
    except:
        await message.answer("⚠️ Введи число, например 1050.5")

@dp.message(CalcStates.waiting_for_course)
async def course_input(message: types.Message, state: FSMContext):
    try:
        course = to_float(message.text)
        if course <= 0:
            raise ValueError
        await state.update_data(course=course)
        await message.answer("📉 Введи курс покупки:")
        await state.set_state(CalcStates.waiting_for_telegram_course)
    except:
        await message.answer("⚠️ Нужен курс в виде положительного числа!")

@dp.message(CalcStates.waiting_for_telegram_course)
async def tg_course_input(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        eur = data["eur"]
        course = data["course"]
        tg_course = to_float(message.text)
        if tg_course <= 0:
            raise ValueError

        usdt_sold = round(eur / course, 2)  # USDT продано
        profit_usdt = round((eur - usdt_sold * tg_course) / tg_course, 4)

        await message.answer(
            (
                f"✅ Ордер: <b>{fmt(eur)} EUR</b>\n"
                f"🏷️ Курс продажи: <b>{fmt(course)}</b>\n"
                f"📉 Курс покупки: <b>{fmt(tg_course)}</b>\n\n"
                f"🔁 Продано USDT: <b>{fmt(usdt_sold, 2)} USDT</b>\n"
                f"💰 Прибыль: <b>{fmt(profit_usdt)} USDT</b>"
            ),
            parse_mode=ParseMode.HTML
        )
        await state.clear()

    except:
        await message.answer("⚠️ Проверь число и попробуй снова.")

# =======================
#  MAIN
# =======================
async def main():
    if not BOT_TOKEN or BOT_TOKEN == "ВАШ_ТОКЕН_СЮДА":
        print("❗ Установи TELEGRAM_BOT_TOKEN или впиши токен в BOT_TOKEN.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
