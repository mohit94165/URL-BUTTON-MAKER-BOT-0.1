import os
import logging
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

class AnimePostCreator:
    def __init__(self):
        self.temp_data = {}
    
    def parse_synopsis(self, text: str) -> dict:
        """Parse text to extract anime information"""
        data = {
            'title': '',
            'season': '',
            'episodes': '',
            'audio': '',
            'quality': '',
            'genres': '',
            'synopsis': '',
            'powered_by': '',
            'image_url': None,
            'download_links': []
        }
        
        # Extract title (the first line after **ANIME :**)
        title_match = re.search(r'\*\*ANIME :\*\*\s*(.+?)(?:\n|\*\*|$)', text, re.IGNORECASE)
        if title_match:
            data['title'] = title_match.group(1).strip()
        
        # Extract season
        season_match = re.search(r'SEASON[:\s]*([0-9]+)', text, re.IGNORECASE)
        if season_match:
            data['season'] = season_match.group(1).strip()
        
        # Extract episodes
        episodes_match = re.search(r'EPISODES[:\s]*([0-9]+)', text, re.IGNORECASE)
        if episodes_match:
            data['episodes'] = episodes_match.group(1).strip()
        
        # Extract audio
        audio_match = re.search(r'AUDIO[:\s]*\[?(.+?)\]?(?:\n|#)', text, re.IGNORECASE)
        if audio_match:
            data['audio'] = audio_match.group(1).strip()
        
        # Extract quality
        quality_match = re.search(r'QUALITY[:\s]*(.+?)(?:\n|GENRES|$)', text, re.IGNORECASE)
        if quality_match:
            data['quality'] = quality_match.group(1).strip()
        
        # Extract genres
        genres_match = re.search(r'GENRES[:\s]*(.+?)(?:\n|>|$)', text, re.IGNORECASE)
        if genres_match:
            data['genres'] = genres_match.group(1).strip()
        
        # Extract synopsis (content between > and **POWERED BY**)
        synopsis_match = re.search(r'>\s*(.+?)\s*\*\*POWERED BY', text, re.DOTALL)
        if synopsis_match:
            data['synopsis'] = synopsis_match.group(1).strip()
        
        # Extract powered by
        powered_match = re.search(r'\*\*POWERED BY[:\s-]*@?(\w+)', text, re.IGNORECASE)
        if powered_match:
            data['powered_by'] = powered_match.group(1).strip()
        
        # Extract download links (URLs in the message)
        url_pattern = r'https?://[^\s]+'
        data['download_links'] = re.findall(url_pattern, text)
        
        return data
    
    def create_post_text(self, data: dict) -> str:
        """Create formatted post text"""
        post_text = f"<b>{data['title']}</b>\n\n"
        
        if data['season']:
            post_text += f"<b>SEASON:</b> {data['season']}\n"
        if data['episodes']:
            post_text += f"<b>EPISODES:</b> {data['episodes']}\n"
        if data['audio']:
            post_text += f"<b>AUDIO:</b> {data['audio']}\n"
        if data['quality']:
            post_text += f"<b>QUALITY:</b> {data['quality']}\n"
        if data['genres']:
            post_text += f"<b>GENRES:</b> {data['genres']}\n\n"
        
        if data['synopsis']:
            post_text += f"<blockquote>{data['synopsis']}</blockquote>\n\n"
        
        if data['powered_by']:
            post_text += f"<b>POWERED BY:</b> @{data['powered_by']}"
        
        return post_text
    
    def create_buttons(self, links: List[str], channel_username: str = None) -> InlineKeyboardMarkup:
        """Create inline keyboard buttons for download links"""
        keyboard = []
        
        # Add quality buttons
        quality_buttons = []
        for i, link in enumerate(links[:3]):  # First 3 links as quality options
            quality_text = ["480P", "720P", "1080P"][i] if i < 3 else f"Link {i+1}"
            quality_buttons.append(
                InlineKeyboardButton(quality_text, url=link)
            )
        
        if quality_buttons:
            keyboard.append(quality_buttons)
        
        # Add channel button if provided
        if channel_username:
            keyboard.append([
                InlineKeyboardButton("Join Channel", url=f"https://t.me/{channel_username}")
            ])
        
        return InlineKeyboardMarkup(keyboard)

# Initialize post creator
post_creator = AnimePostCreator()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    
    welcome_text = """
👋 <b>Welcome to Anime Post Creator Bot!</b>

📝 <b>How to use:</b>
1. Send me anime information in the format shown in the example
2. Include download links in the message
3. I'll format it into a beautiful post with buttons

📋 <b>Example Format:</b>
<code>ANIME: A Misanthrope Teaches a Class for Demi-Humans
SEASON: 01
EPISODES: 13
AUDIO: [Hindi] #Official
QUALITY: 480P • 720P • 1080P
GENRES: Comedy, Drama, Fantasy
> Synopsis text here...
https://download-link1.com
https://download-link2.com
https://download-link3.com</code>

🔧 <b>Admin Commands:</b>
/createpost - Create a post manually
/setchannel @username - Set channel username for join button
"""
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a post from provided text"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide anime information after the command.")
        return
    
    text = " ".join(context.args)
    await process_post(update, context, text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ This bot is for admins only!")
        return
    
    text = update.message.text
    await process_post(update, context, text)

async def process_post(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Process and create the post"""
    try:
        # Parse the message
        data = post_creator.parse_synopsis(text)
        
        if not data['title']:
            await update.message.reply_text("❌ Could not find anime title. Please check the format.")
            return
        
        # Create post text
        post_text = post_creator.create_post_text(data)
        
        # Get channel username from context
        channel_username = context.bot_data.get('channel_username', 'ANIME_TV_INDIA')
        
        # Create buttons
        keyboard = post_creator.create_buttons(data['download_links'], channel_username)
        
        # Send the post
        if update.message.photo:
            # If there's a photo, send it with caption
            photo = update.message.photo[-1]
            await update.message.reply_photo(
                photo=photo.file_id,
                caption=post_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            # Otherwise send as text message
            await update.message.reply_text(
                post_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        
        await update.message.reply_text("✅ Post created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        await update.message.reply_text(f"❌ Error creating post: {str(e)}")

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set channel username for join button"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide channel username: /setchannel @username")
        return
    
    channel_username = context.args[0].replace('@', '')
    context.bot_data['channel_username'] = channel_username
    
    await update.message.reply_text(f"✅ Channel username set to: @{channel_username}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = """
🤖 <b>Anime Post Creator Bot Commands:</b>

<b>For Admins:</b>
/createpost [text] - Create a formatted post
/setchannel @username - Set channel for join button
/help - Show this help message

<b>Format Guidelines:</b>
• Include all anime details
• Add download links at the end
• You can send with or without image
• Use > for synopsis text

<b>Example:</b>
<code>ANIME: Anime Title
SEASON: 01
EPISODES: 12
AUDIO: [Hindi]
QUALITY: 480P • 720P
> This is the synopsis...
https://link1.com
https://link2.com</code>
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not found in environment variables")
    
    # Create Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("createpost", create_post))
    application.add_handler(CommandHandler("setchannel", set_channel))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handler for admins
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_message
    ))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
