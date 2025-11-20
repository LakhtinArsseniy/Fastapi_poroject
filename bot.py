import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = "8215465211:AAGGsx2DwzQiu8MQ8-xFgCxXPZp50SgvsSo"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(KeyboardButton("Мої проблеми"))
keyboard.add(KeyboardButton("Додати проблему"))

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        f"Привіт, {message.from_user.first_name}! Я бот для твоїх проблем.",
        reply_markup=keyboard
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
