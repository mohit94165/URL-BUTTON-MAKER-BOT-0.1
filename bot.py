import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8481849799:AAFakjETXmt6UxK411GSTo36QY6tTUASfZs"
ADMINS = [6728678197]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ========== STATES ==========
class PostMaker(StatesGroup):
    message_text = State()
    button_name = State()
    button_url = State()
    ask_more = State()
    target_chat = State()

# Store buttons
user_buttons = {}

# ========== START ==========
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("🤖 Controller Bot Ready!\nUse /post to create a post with buttons.")

# ========== CREATE POST ==========
@dp.message_handler(commands=['post'])
async def make_post(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.reply("❌ You are not allowed.")

    user_buttons[message.from_user.id] = []
    await message.reply("📝 Send the message text for the post.")
    await PostMaker.message_text.set()

# Step 1 - Message Text
@dp.message_handler(state=PostMaker.message_text)
async def get_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.reply("🔘 Send Button Name")
    await PostMaker.button_name.set()

# Step 2 - Button Name
@dp.message_handler(state=PostMaker.button_name)
async def get_button_name(message: types.Message, state: FSMContext):
    await state.update_data(btn_name=message.text)
    await message.reply("🌐 Send Button URL")
    await PostMaker.button_url.set()

# Step 3 - Button URL
@dp.message_handler(state=PostMaker.button_url)
async def get_button_url(message: types.Message, state: FSMContext):
    data = await state.get_data()
    btn_name = data['btn_name']
    btn_url = message.text

    user_buttons[message.from_user.id].append((btn_name, btn_url))

    await message.reply("➕ Add another button? (yes/no)")
    await PostMaker.ask_more.set()

# Step 4 - More Buttons?
@dp.message_handler(state=PostMaker.ask_more)
async def ask_more_buttons(message: types.Message, state: FSMContext):
    if message.text.lower() == "yes":
        await message.reply("🔘 Send next Button Name")
        await PostMaker.button_name.set()
    else:
        await message.reply("📢 Send target chat ID or @channelusername")
        await PostMaker.target_chat.set()

# Step 5 - Send Post
@dp.message_handler(state=PostMaker.target_chat)
async def send_post(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data['text']
    buttons = user_buttons[message.from_user.id]

    keyboard = InlineKeyboardMarkup(row_width=2)
    for name, url in buttons:
        keyboard.insert(InlineKeyboardButton(name, url=url))

    try:
        await bot.send_message(message.text, text, reply_markup=keyboard)
        await message.reply("✅ Post Sent Successfully!")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

    await state.finish()

# ========== RUN ==========
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
