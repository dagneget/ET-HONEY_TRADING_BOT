import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    Application
)
import database
from languages import get_text
import re
import uuid

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx', '.txt'}

# Regex Patterns for Menu Buttons
REGISTER_PATTERN = r'^(🧍 Register|🧍 ይመዝገቡ)$'
PROFILE_PATTERN = r'^(👤 Profile|👤 መገለጫ)$'
ORDER_PATTERN = r'^(🛒 Make Order|🛒 ይዘዙ)$'
FEEDBACK_PATTERN = r'^(✍️ Feedback|✍️ አስተያየት)$'
SUPPORT_PATTERN = r'^(📞 Contact Support|📞 ድጋፍ ያግኙ)$'
HELP_PATTERN = r'^(ℹ️ Help|ℹ️ እርዳታ)$'
MENU_PATTERN = r'^(☰ Main Menu|☰ ዋና ሜኑ)$'
ADMIN_PATTERN = r'^(👮 Admin|👮 አድሚን)$'
BACK_PATTERN = r'^(⬅️ Return to Main Menu|⬅️ ወደ ዋናው ሜኑ ተመለስ)$'
COMPLAINT_PATTERN = r'^(📝 Complaint|📝 ቅሬታ)$'
INQUIRY_PATTERN = r'^(❓ Inquiry|❓ ጥያቄ)$'
LANGUAGE_PATTERN = r'^(🌐 Language|🌐 ቋንቋ)$'
BLOG_PATTERN = r'^(📰 GPBlog)$'
ADMIN_DASHBOARD_PATTERN = r'^(Admin Dashboard|የአስተዳዳሪ ዳሽቦርድ)$'
ADD_ADMIN_PATTERN = r'^(➕ Add Admin|➕ አድሚን አክል)$'
ADMIN_DASHBOARD_OVERVIEW_PATTERN = r'^(📊 Dashboard Overview|📊 የዳሽቦርድ አጠቃላይ እይታ)$'
ADMIN_MANAGE_PRODUCTS_PATTERN = r'^(🛒 Manage Products|🛒 ምርቶችን ያስተዳድሩ)$'
ADMIN_USER_MESSAGES_PATTERN = r'^(✉️ User Messages|✉️ የተጠቃሚ መልዕክቶች)$'
ADMIN_USER_MANAGEMENT_PATTERN = r'^(👥 User Management|👥 የተጠቃሚ አስተዳደር)$'
ADMIN_REPORTS_LOGS_PATTERN = r'^(📈 Reports & Logs|📈 ሪፖርቶች እና ምዝግብ ማስታወሻዎች)$'
ADMIN_BACK_PATTERN = r'^(⬅️ Back|⬅️ ተመለስ)$'

ADMIN_ADD_PRODUCT_PATTERN = r'^(➕ Add Product|➕ ምርት አክል)$'
ADMIN_LIST_PRODUCTS_PATTERN = r'^(📋 List Products|📋 ምርቶችን ዘርዝር)$'
ADMIN_LIST_USERS_PATTERN = r'^(👥 List All Users|👥 ሁሉንም ተጠቃሚዎች ዘርዝር)$'
ADMIN_EXPORT_ORDERS_PATTERN = r'^(📥 Export Orders|📥 ትዕዛዞችን ላክ \(Export\))$'
ADMIN_VIEW_ALL_TICKETS_PATTERN = r'^(View All|ሁሉንም ይመልከቱ)$'
ADMIN_VIEW_PENDING_TICKETS_PATTERN = r'^(Pending|በመጠባበቅ ላይ)$'
ADMIN_VIEW_CLOSED_TICKETS_PATTERN = r'^(Closed|ተዘግቷል)$'

# Load environment variables
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize Database
database.init_db()

# States for Registration Conversation
FULL_NAME, PHONE, EMAIL, REGION, CUSTOMER_TYPE, CONFIRMATION = range(6)

# States for Support Conversation
WAITING_FOR_SUPPORT_MESSAGE = 10

# States for Order Conversation
PRODUCT_NAME, QUANTITY, DELIVERY_ADDRESS, PAYMENT_TYPE, CONFIRM_ORDER = range(20, 25)

# States for Feedback Conversation
RATING, COMMENT, PHOTO, CONFIRM_FEEDBACK = range(30, 34)

# States for Ticket Conversation
TICKET_CATEGORY, TICKET_SUBJECT, TICKET_MESSAGE, TICKET_ATTACHMENT, CONFIRM_TICKET = range(40, 45)

# States for Account Deletion Conversation
CONFIRM_DELETE = 50

# States for Returning User Conversation
RETURNING_USER_OPTIONS = 60

# States for Admin Reply
ADMIN_REPLY = 70

# States for Adding Product
ADD_PRODUCT_NAME, ADD_PRODUCT_DESC, ADD_PRODUCT_PRICE, ADD_PRODUCT_STOCK, ADD_PRODUCT_QUANTITIES, ADD_PRODUCT_CATEGORY, ADD_PRODUCT_IMAGE = range(80, 87)

# Edit Product States
EDIT_PRODUCT_SELECT, EDIT_PRODUCT_FIELD, EDIT_PRODUCT_NAME, EDIT_PRODUCT_DESC, EDIT_PRODUCT_PRICE, EDIT_PRODUCT_STOCK, EDIT_PRODUCT_IMAGE = range(87, 94)

async def post_init(application: Application):
    """Called after the application is initialized."""
    database.init_db()
    
    # Set bot description (shows before user starts the bot)
    bot_description = (
        "🍯 Welcome to ET HONEY Trading Bot! 🍯\n\n"
        "Your trusted partner for premium Ethiopian honey.\n\n"
        "✨ What we offer:\n"
        "• 100% Pure Ethiopian Honey\n"
        "• Direct from local beekeepers\n"
        "• Fast & reliable delivery\n"
        "• Multiple payment options\n\n"
        "Click START to begin ordering!\n\n"
        "---\n\n"
        "🍯 ወደ ኢቲ ማር ንግድ ቦት እንኳን በደህና መጡ! 🍯\n\n"
        "ለተሻለ የኢትዮጵያ ማር የእርስዎ አማራጭ።\n\n"
        "START የሚለውን ጠቅ ያድርጉ!"
    )
    
    bot_short_description = (
        "🍯 Premium Ethiopian Honey Trading Bot - Order pure honey with fast delivery!"
    )
    
    try:
        await application.bot.set_my_description(description=bot_description)
        await application.bot.set_my_short_description(short_description=bot_short_description)
        logging.info("Bot description set successfully")
    except Exception as e:
        logging.error(f"Failed to set bot description: {e}")
    commands = [
        BotCommand("start", "Open Main Menu"),
    ]
    await application.bot.set_my_commands(commands)

async def admin_dashboard_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays an overview of the bot's statistics for admins."""
    user = update.effective_user
    username = user.username
    if not await is_admin(username):
        await update.message.reply_text("You are not authorized to access the admin dashboard.")
        return

    # Fetching data
    total_users = database.get_total_users()
    total_messages = database.get_total_messages()
    pending_messages = database.get_pending_messages()
    resolved_messages = database.get_resolved_messages()
    total_revenue = database.get_total_revenue()
    total_orders = database.get_total_orders_count()
    system_alerts = "No active system alerts."

    message = (
        f"*📊 Admin Dashboard Overview*\n\n"
        f"💰 Total Revenue: ${total_revenue:,.2f}\n"
        f"🛒 Total Orders: {total_orders}\n"
        f"👥 Total Users: {total_users}\n"
        f"✉️ Total Messages/Inquiries: {total_messages}\n"
        f"⏳ Pending Messages: {pending_messages}\n"
        f"✅ Resolved Messages: {resolved_messages}\n\n"
        f"🚨 System Alerts: {system_alerts}\n\n"
        f"_Use the ⬅️ Back button from the keyboard menu to return._"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(text=message, parse_mode='Markdown')
    else:
        await update.message.reply_text(text=message, parse_mode='Markdown')

async def admin_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_status=None) -> None:
    """Displays a list of user messages/tickets for admins with filtering options."""
    # Determine the status from callback data if available, otherwise use argument
    if update.callback_query and not filter_status:
         data_parts = update.callback_query.data.split(':')
         filter_status = data_parts[1] if len(data_parts) > 1 else None
    
    if update.callback_query:
        await update.callback_query.answer()
        username = update.effective_user.username
    else:
        username = update.effective_user.username

    if not await is_admin(username):
        if update.callback_query:
             await update.callback_query.message.reply_text("You are not authorized to access this feature.")
        else:
             await update.message.reply_text("You are not authorized.")
        return

    # Treat 'all' as None for DB query
    if filter_status == 'all':
        filter_status = None

    tickets = database.get_all_tickets(filter_status)
    
    status_label = filter_status.capitalize() if filter_status else "All"
    text = f"✉️ *User Messages / Tickets ({status_label})*\n\n"
    
    # Persistent Menu for filtering - Always show this
    lang = get_user_lang(update, context) or 'en'
    keyboard = [
        [get_text(lang, 'btn_view_all_tickets'), get_text(lang, 'btn_view_pending_tickets'), get_text(lang, 'btn_view_closed_tickets')],
        [get_text(lang, 'admin_back')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if not tickets:
        text += f"No {filter_status} tickets found." if filter_status else "No tickets found."
    else:
        for t in tickets[:5]: # Show last 5 for brevity in menu
            status_icon = "🟢" if t['status'] == 'Open' else "🔴" if t['status'] == 'closed' else "🟡"
            text += f"{status_icon} #{t['id']}: {t['subject']} ({t['status']})\n"
            # Inline buttons for viewing specific tickets (these are per-item actions, consistent with design)
            # We can't put these in persistent menu easily as they are dynamic.
            # So we show the list text, and if they want to view details, they likely need an ID or we provide inline buttons JUST for the list items in the text message?
            # The prompt said "like under admin... continued like this". 
            # Usually for dynamic items inline buttons are best. But the prompt implies persistent structure.
            # I will keep inline buttons for the *items* themselves in the text message, but the *navigation* (Back, Filter) is persistent.
    
    # We need to send the persistent menu. But we also want to show the list items clickable.
    # Telegram allows text message with InlineKeyboard OR ReplyKeyboard, not both on same message.
    # So we send the text with the list items (maybe just text list if we can't use inline)
    # OR we send TWO messages: one with the list (and inline buttons), and one with the persistent menu.
    # LIMITATION: ReplyKeyboard is attached to a message.
    # STRATEGY: Send the list with INLINE buttons for "View #ID", and the ReplyKeyboard is attached to that message (or a follow up).
    # wait, you can attach ReplyMarkup to a message that has InlineKeyboard? NO.
    # Check library: Can't have both.
    # SOLUTION: The requested "persistent buttons" are for NAVIGATION/FILTERS. 
    # For Selecting a specific ticket, we either need a text command "View 123" or use inline buttons on the list message.
    # If we use inline buttons for items, we lose the persistent buttons on THAT message.
    # However, the persistent buttons from the PREVIOUS message (the menu itself) remain visible if input_field_placeholder is used or if we just send a "Menu updated" message.
    # Better User Experience: 
    # 1. Send the list of tickets as a text message with INLINE buttons to "View Ticket #1".
    # 2. SEPARATELY send a "Menu Options" message with the ReplyKeyboardMarkup (Back, Filter buttons).
    
    # Let's try sending just the text list first, and assuming the User will just click the filters.
    # For viewing a specific ticket, we might need a "View Ticket" button in persistent menu that asks for ID? Or just keep inline for items.
    # Let's keep inline for items, and send the persistent menu in a separate message "Select an option:".
    
    # Actually, simpler: The Prompt asked for structure "like admin dashboard".
    # Admin dashboard has persistent buttons.
    # So "User Messages" screen should have persistent buttons for "View All", "Pending", "Back".
    # The content (the list) appears in the chat.
    # If I want to click a ticket, I can use an inline button on that specific message bubble.
    # The persistent menu stays at the bottom.
    
    # Build inline keyboard for ticket items
    item_reply_markup = None
    if tickets:
        keyboard_buttons = []
        for ticket in tickets:
            customer = database.get_customer_by_telegram_id(ticket['user_id'])
            name = customer['full_name'] if customer else "Unknown User"
            username = customer['username'] if customer else ""
            user_display = f"{name} (@{username})" if username else name
            text += f"ID: {ticket['id']} | User: {user_display} | Subject: {ticket['subject']} | Status: {ticket['status']}\n"
            keyboard_buttons.append([InlineKeyboardButton(f"View Ticket {ticket['id']}", callback_data=f'admin_view_ticket:{ticket['id']}')])
        
        item_reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    # Send the message with appropriate markup
    if update.callback_query:
        if item_reply_markup:
            await update.callback_query.message.reply_text(text, reply_markup=item_reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.message.reply_text(text, parse_mode='Markdown')
        await update.callback_query.message.reply_text("👇 Options:", reply_markup=reply_markup)
    else:
        if item_reply_markup:
            await update.message.reply_text(text, reply_markup=item_reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
        await update.message.reply_text("👇 Options:", reply_markup=reply_markup)

async def admin_view_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the messages within a specific ticket for admins."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not await is_admin(query.from_user.username):
        await query.message.reply_text("You are not authorized to access this feature.")
        return

    try:
        ticket_id = int(query.data.split(':')[1])
    except (IndexError, ValueError):
        await query.message.reply_text("Invalid ticket ID.")
        return

    ticket = database.get_ticket(ticket_id)
    if not ticket:
        await query.message.reply_text("Ticket not found.")
        return

    messages = database.get_messages_for_ticket(ticket_id)
    customer = database.get_customer_by_telegram_id(ticket['user_id'])
    name = customer['full_name'] if customer else "Unknown User"
    username = customer['username'] if customer else ""
    user_display = f"{name} (@{username})" if username else name

    message_text = f"*✉️ Ticket #{ticket_id} with {user_display} (Status: {ticket['status']})*\n\n"
    for msg in messages:
        message_text += f"*{msg['sender_type'].capitalize()}*: {msg['message']}\n"

    context.user_data['admin_reply_ticket_id'] = ticket_id
    keyboard = [
        [InlineKeyboardButton("↩️ Reply", callback_data=f'admin_reply_to_ticket:{ticket_id}')],
        [InlineKeyboardButton("✅ Resolve Ticket", callback_data=f'admin_resolve_ticket:{ticket_id}')],
        [InlineKeyboardButton("⬅️ Back to Messages", callback_data='admin_user_messages')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        # Ignore "Message is not modified" error
        if "Message is not modified" in str(e):
            pass
        else:
            logging.error(f"Error updating ticket view: {e}")

async def admin_reply_to_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the admin reply conversation."""
    query = update.callback_query
    await query.answer()
    
    try:
        ticket_id = int(query.data.split(':')[1])
    except (IndexError, ValueError):
        await query.message.reply_text("Invalid ticket ID.")
        return ConversationHandler.END

    context.user_data['reply_ticket_id'] = ticket_id
    
    ticket = database.get_ticket(ticket_id)
    if not ticket:
        await query.message.reply_text("Ticket not found.")
        return ConversationHandler.END

    customer = database.get_customer_by_telegram_id(ticket['user_id'])
    name = customer['full_name'] if customer else "User"

    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"📝 Please type your reply for *{name}*:", reply_markup=reply_markup, parse_mode='Markdown')
    return ADMIN_REPLY

async def admin_receive_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the admin's reply message and sends it to the user."""
    text = update.message.text
    ticket_id = context.user_data.get('reply_ticket_id')
    
    if not ticket_id:
        await update.message.reply_text("Session expired. Please select the ticket again.")
        return ConversationHandler.END

    # Save message to DB
    database.add_message(ticket_id, 'admin', text)
    
    # Update ticket status if needed
    database.update_ticket_status(ticket_id, 'Open') 
    
    # Notify User
    ticket = database.get_ticket(ticket_id)
    if ticket:
        user_id = ticket['user_id'] # Telegram ID
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"👨‍💼 *Support Reply (Ticket #{ticket_id})*:\n\n{text}\n\n_Type a message to reply back._",
                parse_mode='Markdown'
            )
            await update.message.reply_text(f"✅ Reply sent to user.")
        except Exception as e:
            await update.message.reply_text(f"❌ Reply saved, but failed to send notification: {e}")
    else:
        await update.message.reply_text("❌ Ticket not found.")
        
    return ConversationHandler.END

async def admin_resolve_ticket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resolves/closes a ticket."""
    query = update.callback_query
    await query.answer()
    
    ticket_id = int(query.data.split(':')[1])
    database.close_ticket(ticket_id)
    
    await query.message.reply_text(f"✅ Ticket #{ticket_id} has been resolved/closed.")
    # Refresh view
    await admin_view_ticket(update, context)

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the admin dashboard menu."""
    username = update.effective_user.username
    if not await is_admin(username):
        await update.message.reply_text("You are not authorized to access the admin dashboard.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Dashboard Overview", callback_data='admin_dashboard_overview')],
        [InlineKeyboardButton("🛒 Manage Products", callback_data='admin_products')],
        [InlineKeyboardButton("✉️ User Messages", callback_data='admin_user_messages')],
        [InlineKeyboardButton("👥 User Management", callback_data='admin_user_management')],
        [InlineKeyboardButton("📈 Reports & Logs", callback_data='admin_reports_logs')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Welcome to the Admin Dashboard! Please choose an option:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Welcome to the Admin Dashboard! Please choose an option:", reply_markup=reply_markup)

async def setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Temporarily sets a user as admin by username."""
    requester_username = update.effective_user.username
    if not await is_admin(requester_username):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setadmin <username>")
        return

    target_username = context.args[0].lstrip('@') # Remove @ if present
    database.set_admin_by_username(target_username)
    await update.message.reply_text(f"User @{target_username} has been temporarily set as admin.")

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username
    lang = context.user_data.get('language', 'en')
    
    if not await is_admin(username):
        await update.message.reply_text("⛔ You are not authorized to access the admin area.")
        return

    # Show persistent Admin Sub-menu
    keyboard = [
        [get_text(lang, 'admin_dashboard'), get_text(lang, 'add_admin_title')],
        [get_text(lang, 'back_button')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("👮 Admin Menu:", reply_markup=reply_markup)

async def admin_dashboard_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the persistent admin dashboard sub-menu."""
    # This just calls the existing admin_menu which shows the inline dashboard
    # Now updated to show persistent sub-menu
    user = update.effective_user
    username = user.username
    lang = context.user_data.get('language', 'en')

    if not await is_admin(username):
        await update.message.reply_text("⛔ You are not authorized.")
        return

    keyboard = [
        [get_text(lang, 'dashboard_overview'), get_text(lang, 'manage_products')],
        [get_text(lang, 'user_messages'), get_text(lang, 'user_management')],
        [get_text(lang, 'reports_logs')],
        [get_text(lang, 'admin_back')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("👮 Admin Dashboard Menu:", reply_markup=reply_markup)

async def admin_add_admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username
    lang = context.user_data.get('language', 'en')

    if not await is_admin(username):
        await update.message.reply_text("⛔ You are not authorized.")
        return
        
    users = database.get_all_customers()
    if not users:
        await update.message.reply_text("No users found to promote.")
        return

    keyboard = []
    for u in users:
        # Show name and username if available
        label = u['full_name']
        if u['username']:
            label += f" (@{u['username']})"
        if u['is_admin']:
            label += " (Admin)"
        
        # Callback data: promote_admin:<telegram_id>
        keyboard.append([InlineKeyboardButton(label, callback_data=f"promote_admin:{u['telegram_id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(lang, 'select_user_promote'), reply_markup=reply_markup)

async def promote_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(':')
    target_id = int(data[1])
    lang = context.user_data.get('language', 'en')
    
    # Check if target is already admin? database.get_customer returns Row
    target_user = database.get_customer_by_telegram_id(target_id)
    
    if target_user['is_admin']:
        await query.message.reply_text(f"{target_user['full_name']} is already an admin.")
    else:
        database.set_admin_status(target_id, 1)
        name = target_user['full_name']
        msg = get_text(lang, 'admin_promoted', name=name)
        await query.message.reply_text(msg)

async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("English 🇬🇧", callback_data='lang_en')],
        [InlineKeyboardButton("Amharic 🇪🇹", callback_data='lang_am')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "Please select your language / ቋንቋ ይምረጡ:"
    if update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    user_id = query.from_user.id
    
    context.user_data['language'] = lang
    
    # Update DB if user exists
    customer = database.get_customer_by_telegram_id(user_id)
    if customer:
        database.update_customer_language(user_id, lang)
        
    await query.message.reply_text(get_text(lang, 'language_set'))
    await start(update, context)

def get_user_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if 'language' in context.user_data:
        return context.user_data['language']
    
    customer = database.get_customer_by_telegram_id(user_id)
    if customer and 'language' in customer.keys() and customer['language']:
        return customer['language']
    
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a message with a persistent keyboard menu."""
    lang = get_user_lang(update, context)
    if not lang:
        await choose_language(update, context)
        return

    # Use ReplyKeyboardMarkup for persistent menu (Grid Layout)
    # Updated Persistent Menu Layout
    keyboard = [
        [get_text(lang, 'admin_button'), get_text(lang, 'register')],
        [get_text(lang, 'menu_button')],
        [get_text(lang, 'contact_support'), get_text(lang, 'about_help')],
        [get_text(lang, 'language')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_msg = get_text(lang, 'welcome')
    if update.message:
        await update.message.reply_text(welcome_msg, reply_markup=reply_markup)
    elif update.callback_query:
         # When returning from a conversation or other flow
        await update.callback_query.message.reply_text(welcome_msg, reply_markup=reply_markup)

async def check_registration_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    customer = database.get_customer_by_telegram_id(user_id)
    lang = get_user_lang(update, context) or 'en'

    if not customer:
        message = get_text(lang, 'not_registered')
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return False
    
    # Pending status allows access now
    
    if customer['status'] == 'Rejected':
        message = "Your registration was rejected. Please contact support or re-register."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return False

    if customer['status'] == 'Deleted':
        message = get_text(lang, 'account_deleted')
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return False

    if customer['status'] == 'Approved':
        return True
    
    return False

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the registration process."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    logging.info(f"start_registration: effective_user.username is: {username}")
    if not username:
        lang = get_user_lang(update, context) or 'en'
        message = "To register, you must have a Telegram username. Please set one in your Telegram settings and try again."
        keyboard = [[InlineKeyboardButton(get_text(lang, 'cancel'), callback_data='cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
        return ConversationHandler.END
    customer = database.get_customer_by_telegram_id(user_id)
    logging.info(f"start_registration: Customer for user_id {user_id}: {customer}")

    if customer:
        if customer['status'] == 'Approved':
            message = "You are already registered and approved!" 
        elif customer['status'] == 'Pending':
            message = "You have a pending registration. Please wait for admin approval." 
        elif customer['status'] == 'Deleted':
            keyboard = [
                [InlineKeyboardButton("Keep My Old Account", callback_data='reactivate_account')],
                [InlineKeyboardButton("Register as New (Delete Old Account)", callback_data='register_new_account')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text("It looks like you have a deleted account. Would you like to keep your old account or register as new?", reply_markup=reply_markup)
            else:
                await update.message.reply_text("It looks like you have a deleted account. Would you like to keep your old account or register as new?", reply_markup=reply_markup)
            return RETURNING_USER_OPTIONS
        else: # Rejected or any other status that should allow re-registration
            keyboard = [
                [InlineKeyboardButton("Register as New (Delete Old Account)", callback_data='register_new_account')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text("Your previous registration was rejected. Would you like to permanently delete your old record and register as new?", reply_markup=reply_markup)
            else:
                await update.message.reply_text("Your previous registration was rejected. Would you like to permanently delete your old record and register as new?", reply_markup=reply_markup)
            return RETURNING_USER_OPTIONS

        if customer['status'] != 'Deleted' and customer['status'] != 'Rejected': # Only send this message if not a deleted or rejected account
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(message)
            else:
                await update.message.reply_text(message)
            return ConversationHandler.END

    lang = get_user_lang(update, context) or 'en'
    keyboard = [[InlineKeyboardButton(get_text(lang, 'cancel'), callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(get_text(lang, 'register_intro'), reply_markup=reply_markup, parse_mode='Markdown')
    else: # triggered via command
        await update.message.reply_text(get_text(lang, 'register_intro'), reply_markup=reply_markup, parse_mode='Markdown')
        
    return FULL_NAME

async def receive_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores full name and asks for phone number."""
    user_input = update.message.text
    # Validation placeholder
    if len(user_input) < 3:
        await update.message.reply_text("Name is too short. Please enter your full name:")
        return FULL_NAME
    
    context.user_data['full_name'] = user_input
    lang = get_user_lang(update, context) or 'en'
    keyboard = [[InlineKeyboardButton(get_text(lang, 'cancel'), callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(lang, 'enter_phone'), reply_markup=reply_markup, parse_mode='Markdown')
    return PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores phone and asks for email."""
    user_input = update.message.text
    # Validation placeholder (e.g., regex check)
    if not user_input.isdigit(): # Simple check
         await update.message.reply_text("Please enter a valid phone number (digits only):")
         return PHONE

    context.user_data['phone'] = user_input
    lang = get_user_lang(update, context) or 'en'
    keyboard = [[InlineKeyboardButton(get_text(lang, 'cancel'), callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(lang, 'enter_email'), reply_markup=reply_markup, parse_mode='Markdown')
    return EMAIL

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores email and asks for region."""
    user_input = update.message.text
    
    if user_input.lower() == 'skip':
        context.user_data['email'] = None
    else:
        # Validation placeholder
        if "@" not in user_input:
            await update.message.reply_text("Please enter a valid email address or type 'skip':")
            return EMAIL
        context.user_data['email'] = user_input
    
    lang = get_user_lang(update, context) or 'en'
    keyboard = [[InlineKeyboardButton(get_text(lang, 'cancel'), callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(lang, 'enter_region'), reply_markup=reply_markup, parse_mode='Markdown')
    return REGION

async def receive_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores region and asks for customer type."""
    user_input = update.message.text
    context.user_data['region'] = user_input
    
    lang = get_user_lang(update, context) or 'en'
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'new_customer'), callback_data='New'),
         InlineKeyboardButton(get_text(lang, 'returning_customer'), callback_data='Returning')],
        [InlineKeyboardButton(get_text(lang, 'cancel'), callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(lang, 'customer_type_prompt'), reply_markup=reply_markup, parse_mode='Markdown')
    return CUSTOMER_TYPE

async def receive_customer_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores customer type and asks for confirmation."""
    query = update.callback_query
    await query.answer()
    context.user_data['customer_type'] = query.data
    
    # Summary
    lang = get_user_lang(update, context) or 'en'
    summary = (
        f"{get_text(lang, 'confirm_reg_title')}\n\n"
        f"👤 Name: {context.user_data['full_name']}\n"
        f"📞 Phone: {context.user_data['phone']}\n"
        f"📧 Email: {context.user_data['email']}\n"
        f"📍 Region: {context.user_data['region']}\n"
        f"🏷 Type: {context.user_data['customer_type']}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'confirm'), callback_data='confirm'),
         InlineKeyboardButton(get_text(lang, 'cancel'), callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    return CONFIRMATION

async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves to DB and notifies admin."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel':
        await query.message.reply_text("Registration cancelled.")
        return ConversationHandler.END
    
    # Save to DB
    data = {
        'telegram_id': update.effective_user.id,
        'username': update.effective_user.username,
        'full_name': context.user_data['full_name'],
        'phone': context.user_data['phone'],
        'email': context.user_data['email'],
        'region': context.user_data['region'],
        'customer_type': context.user_data['customer_type']
    }
    
    customer_id = database.add_customer(data)
    lang = get_user_lang(update, context) or 'en'
    
    # Prompt for Order Now or Later
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'order_now'), callback_data='order')],
        [InlineKeyboardButton(get_text(lang, 'order_later'), callback_data='order_later')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(get_text(lang, 'reg_success'), reply_markup=reply_markup)
    
    # Notify Admin (Informational)
    admin_id = os.getenv("ADMIN_ID")
    if admin_id and admin_id != "your_admin_id_here":
        try:
            message = (
                f"ℹ️ *New Customer Registered*\n\n"
                f"ID: {customer_id}\n"
                f"Telegram ID: {data['telegram_id']}\n"
                f"Username: @{data['username']}\n"
                f"Name: {data['full_name']}\n"
                f"Phone: {data['phone']}\n"
                f"Email: {data['email']}\n"
                f"Region: {data['region']}\n"
                f"Type: {data['customer_type']}\n"
                f"Status: Approved (Auto)"
            )
            await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Failed to send admin notification: {e}")
            
    return ConversationHandler.END

async def order_later_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(update, context) or 'en'
    await query.message.reply_text(get_text(lang, 'order_later_msg'))

async def handle_returning_user_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the choice of a returning user with a deleted account."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == 'reactivate_account':
        database.update_customer_status_by_telegram_id(user_id, 'Approved') # Reactivate as Approved
        await query.message.reply_text("Your old account has been reactivated and is now Approved! You can start ordering.")

        # Notify Admin about account reactivation
        admin_id = os.getenv("ADMIN_ID")
        if admin_id and admin_id != "your_admin_id_here":
            try:
                customer = database.get_customer_by_telegram_id(user_id)
                if customer:
                    message = (
                        f"ℹ️ *Account Reactivated*\n\n"
                        f"User: {customer['full_name']} (ID: {user_id})\n"
                        f"Username: @{customer['username']}\n"
                        f"Status: Approved (Auto)\n"
                    )
                    await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Failed to send admin notification for account reactivation: {e}")
        return ConversationHandler.END
    elif query.data == 'register_new_account':
        database.permanently_delete_customer(user_id)
        await query.message.reply_text("Your old account has been permanently deleted. Let's start your new registration! Please enter your *Full Name*:", parse_mode='Markdown')
        return FULL_NAME # Restart registration
    return ConversationHandler.END

async def start_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiates the account deletion process."""
    if update.callback_query:
        await update.callback_query.answer()
    
    user_id = update.effective_user.id
    customer = database.get_customer_by_telegram_id(user_id)
    
    msg_sender = update.message if update.message else update.callback_query.message

    if not customer:
        await msg_sender.reply_text("You don't have an account to delete.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("Yes, delete my account", callback_data='confirm_delete'),
         InlineKeyboardButton("No, keep my account", callback_data='cancel_delete')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await msg_sender.reply_text("Are you sure you want to delete your account? This action is irreversible and will remove all your associated data (orders, tickets, feedback).", reply_markup=reply_markup)
    return CONFIRM_DELETE

async def confirm_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles account deletion confirmation."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == 'confirm_delete':
        database.permanently_delete_customer(user_id)
        await query.message.reply_text("Your account and all associated data have been permanently deleted. We're sad to see you go!")
    else:
        await query.message.reply_text("Account deletion cancelled. Your account remains active.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the conversation, returning to home."""
    msg = 'Process cancelled.'
    if update.message:
        await update.message.reply_text(msg)
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg)
    
    # Return to home menu
    await start(update, context)
    return ConversationHandler.END

async def is_admin(username):
    customer = database.get_customer_by_username(username)
    if customer:
        return customer['is_admin'] == 1
    return False

async def notify_all_admins(context: ContextTypes.DEFAULT_TYPE, message: str, parse_mode='Markdown', reply_markup=None):
    """Send notification to all admins."""
    admin_ids = database.get_all_admin_telegram_ids()
    
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message, parse_mode=parse_mode, reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Failed to send notification to admin {admin_id}: {e}")

async def admin_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles admin approval/rejection actions."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(':')
    if len(data) != 4 or data[0] != 'admin':
        return

    action = data[1] # approve or reject
    # entity = data[2] # orders (others removed)
    entity_id = int(data[3])
    
    # Check if order/entity already processed to prevent conflicts
    if 'orders' in query.data:
        order = database.get_order(entity_id)
        if not order:
            await query.answer("⚠️ Order not found!", show_alert=True)
            return
        
        # Check if already processed
        if order['status'] != 'Pending':
            await query.answer(
                f"⚠️ This order was already {order['status']} by another admin!",
                show_alert=True
            )
            # Update the message to show it's already processed
            try:
                new_text = query.message.text + f"\n\n⚠️ *ALREADY {order['status'].upper()}*"
                await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=None)
            except:
                pass
            return
    
    if action == 'approve':
        if 'orders' in query.data:
            database.update_order_status(entity_id, 'Approved')
            new_text = query.message.text + "\n\n✅ *ORDER APPROVED*"
            await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=None)
            
            # Notify user
            order = database.get_order(entity_id)
            if order and order['user_id']:
                 try:
                    await context.bot.send_message(chat_id=order['user_id'], text=f"🎉 Your Order #{entity_id} has been confirmed! We are processing it.")
                 except Exception as e:
                    logging.error(f"Could not notify user: {e}")

    elif action == 'reject':
        if 'orders' in query.data:
            database.update_order_status(entity_id, 'Rejected')
            new_text = query.message.text + "\n\n❌ *ORDER REJECTED*"
            await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=None)
            
            # Notify user
            order = database.get_order(entity_id)
            if order and order['user_id']:
                 try:
                    await context.bot.send_message(chat_id=order['user_id'], text=f"❌ Your Order #{entity_id} could not be processed. Please contact support.")
                 except Exception as e:
                    logging.error(f"Could not notify user: {e}")

# --- Support / Ticket Handlers ---

async def start_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_registration_status(update, context):
        return ConversationHandler.END
    """Initiates a support ticket (Inquiry, Complaint)."""
    # Check if user already has an active ticket
    active_ticket = database.get_active_ticket(update.effective_user.id)
    if active_ticket:
        message = (
            f"⚠️ You already have an open ticket (#{active_ticket['id']}).\n"
            f"Please wait for a response or reply to it directly by typing your message here."
        )
        if update.callback_query:
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return ConversationHandler.END

    category = "Support"
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        category = query.data # This will be 'Inquiry' or 'Complaint'
        if category == 'contact_support':
            category = 'Support'
    else: # triggered via command
        category = "Inquiry" # Default for command if not specified
        if context.args and context.args[0] in ["Inquiry", "Complaint"]:
            category = context.args[0]

    context.user_data['ticket_category'] = category
    context.user_data['ticket_subject'] = f"New {category}" # Auto-set subject
    
    text = f"Please describe your {category} or question below:"
    
    keyboard = [[InlineKeyboardButton(get_text(lang, 'cancel'), callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    return TICKET_MESSAGE

async def receive_ticket_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores category and asks for subject. (Deprecated flow but kept for compatibility)"""
    query = update.callback_query
    await query.answer()
    
    category = query.data
    context.user_data['ticket_category'] = category
    context.user_data['ticket_subject'] = f"New {category}"
    
    await query.message.reply_text(f"Please describe your {category} or question below:", parse_mode='Markdown')
    return TICKET_MESSAGE

async def receive_ticket_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores subject and asks for message. (Deprecated)"""
    # This function is skipped in the new flow
    user_input = update.message.text
    context.user_data['ticket_subject'] = user_input
    await update.message.reply_text("Please describe your issue or question in detail:", parse_mode='Markdown')
    return TICKET_MESSAGE

async def receive_ticket_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores message and asks for attachment."""
    user_input = update.message.text
    if len(user_input) < 2:
        await update.message.reply_text("Message is too short. Please provide more details:")
        return TICKET_MESSAGE
        
    context.user_data['ticket_message'] = user_input
    
    keyboard = [[InlineKeyboardButton("Skip Attachment", callback_data='skip_attachment')], [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Would you like to attach a photo or document? (Optional)\n\nSend a file or click *Skip Attachment*.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return TICKET_ATTACHMENT

async def receive_ticket_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles attachment upload."""
    user_id = update.effective_user.id
    category = context.user_data['ticket_category']
    subject = context.user_data['ticket_subject']
    message_text = context.user_data['ticket_message']

    # 1. Create a preliminary ticket entry to get an ID
    ticket_id = database.create_ticket(user_id, category, subject, message_text)
    context.user_data['ticket_id'] = ticket_id

    # Determine if photo or document
    file_obj = None
    file_extension = ""
    if update.message.photo:
        file_obj = await update.message.photo[-1].get_file()
        file_extension = ".jpg"
    elif update.message.document:
        file_obj = await update.message.document.get_file()
        file_extension = os.path.splitext(update.message.document.file_name)[1] or ""
    else:
        await update.message.reply_text("Please send a photo or document, or click Skip.")
        return TICKET_ATTACHMENT

    file_extension = file_extension.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        await update.message.reply_text(f"Unsupported file type: *{file_extension}*. Please send a file with one of the allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}.", parse_mode='Markdown')
        return TICKET_ATTACHMENT

    # 2. Create structured uploads directory if not exists
    upload_dir = os.path.join('uploads', 'tickets')
    os.makedirs(upload_dir, exist_ok=True)
    
    # 3. Generate unique filename with ticket_id
    filename = f"{ticket_id}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    await file_obj.download_to_drive(file_path)
    context.user_data['ticket_attachment'] = file_path
    
    # 4. Update the ticket entry with the attachment path
    database.update_ticket_attachment_path(ticket_id, file_path)
    
    await show_ticket_confirmation(update, context)
    return CONFIRM_TICKET

async def skip_ticket_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles skipping attachment."""
    query = update.callback_query
    await query.answer()
    context.user_data['ticket_attachment'] = None
    
    # Create ticket (since we skipped attachment where it's usually created)
    user_id = update.effective_user.id
    category = context.user_data['ticket_category']
    subject = context.user_data['ticket_subject']
    message_text = context.user_data['ticket_message']
    
    ticket_id = database.create_ticket(user_id, category, subject, message_text)
    context.user_data['ticket_id'] = ticket_id
    
    await show_ticket_confirmation(update, context)
    return CONFIRM_TICKET

async def show_ticket_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows summary and confirmation buttons."""
    category = context.user_data['ticket_category']
    subject = context.user_data['ticket_subject']
    message = context.user_data['ticket_message']
    attachment = context.user_data.get('ticket_attachment')
    
    summary = (
        f"*Confirm Ticket Details:*\n\n"
        f"📂 Type: {category}\n"
        f"📌 Subject: {subject}\n"
        f"📝 Message: {message}\n"
        f"📎 Attachment: {'Yes' if attachment else 'No'}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Submit Ticket", callback_data='confirm_ticket'),
         InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')

async def confirm_ticket_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves ticket to DB and notifies admin."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel':
        await query.message.reply_text("Ticket creation cancelled.")
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    category = context.user_data['ticket_category']
    subject = context.user_data['ticket_subject']
    message_text = context.user_data['ticket_message']
    attachment_path = context.user_data.get('ticket_attachment')
    ticket_id = context.user_data['ticket_id'] # Retrieve the existing ticket_id
    
    # No need to call database.create_ticket here, as it was already created in receive_ticket_attachment
    
    await query.message.reply_text(f"✅ Ticket #{ticket_id} created! We will review it shortly.")
    
    # Notify All Admins
    admin_msg = (
        f"🛠 *New Support Ticket*\n\n"
        f"Ticket: #{ticket_id}\n"
        f"Type: {category}\n"
        f"Subject: {subject}\n"
        f"User: {update.effective_user.full_name} (@{update.effective_user.username or 'NoUsername'}) (ID: {user_id})\n\n"
        f"{message_text}"
    )
    await notify_all_admins(context, admin_msg)
    
    if attachment_path:
        for admin_id in database.get_all_admin_telegram_ids():
            try:
                if attachment_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                    await context.bot.send_photo(chat_id=admin_id, photo=open(attachment_path, 'rb'), caption=f"Attachment for Ticket #{ticket_id}")

                else:
                     await context.bot.send_document(chat_id=admin_id, document=open(attachment_path, 'rb'), caption=f"Attachment for Ticket #{ticket_id}")

            except Exception as e:
                logging.error(f"Failed to notify admin: {e}")
            
    return ConversationHandler.END

async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles admin replies to forwarded support messages."""
    admin_id = str(update.effective_user.id)
    configured_admin_id = os.getenv("ADMIN_ID")
    
    if admin_id != configured_admin_id:
        return # Ignore non-admin replies
        
    if not update.message.reply_to_message:
        return # Ignore if not a reply
        
    # Extract Ticket ID from the original message text
    original_text = update.message.reply_to_message.text
    # Regex to find "Ticket: #123" or "Ticket #123"
    match = re.search(r"Ticket:? #(\d+)", original_text)
    
    if not match:
        await update.message.reply_text("⚠️ Could not find Ticket ID in the message you replied to.")
        return
        
    ticket_id = int(match.group(1))
    reply_text = update.message.text
    
    # Check if ticket exists
    ticket = database.get_ticket(ticket_id)
    if not ticket:
        await update.message.reply_text("⚠️ Ticket not found.")
        return
        
    # Save Admin Message
    database.add_message(ticket_id, 'admin', reply_text)
    
    # Send to User
    user_id = ticket['user_id']
    try:
        user_message = (
            f"👨‍💼 *Support Reply (Ticket #{ticket_id})*\n\n"
            f"{reply_text}"
        )
        await context.bot.send_message(chat_id=user_id, text=user_message, parse_mode='Markdown')
        await update.message.reply_text("✅ Reply sent to user.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send to user: {e}")

# --- Admin Product Management ---

async def admin_products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the product management menu."""
    if update.callback_query:
        await update.callback_query.answer()
        user = update.effective_user
        query_msg = update.callback_query.message
    else:
        user = update.effective_user
        query_msg = update.message
        
    lang = get_user_lang(update, context) or 'en'

    if not await is_admin(user.username):
        await query_msg.reply_text("You are not authorized.")
        return

    keyboard = [
        [get_text(lang, 'btn_add_product'), get_text(lang, 'btn_list_products')],
        [get_text(lang, 'admin_back')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    msg = "🛒 *Product Management*\n\nSelect an option:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_status=None) -> None:
    """Displays a list of user messages/tickets for admins with filtering options."""
    # Determine the status from callback data if available, otherwise use argument
    if update.callback_query and not filter_status:
         data_parts = update.callback_query.data.split(':')
         filter_status = data_parts[1] if len(data_parts) > 1 else None
    
    if update.callback_query:
        await update.callback_query.answer()
        username = update.effective_user.username
    else:
        username = update.effective_user.username

    if not await is_admin(username):
        if update.callback_query:
             await update.callback_query.message.reply_text("You are not authorized to access this feature.")
        else:
             await update.message.reply_text("You are not authorized.")
        return

    # Treat 'all' as None for DB query
    if filter_status == 'all':
        filter_status = None

    tickets = database.get_all_tickets(filter_status)
    
    status_label = filter_status.capitalize() if filter_status else "All"
    text = f"✉️ *User Messages / Tickets ({status_label})*\n\n"
    
    # Persistent Menu for filtering
    lang = get_user_lang(update, context) or 'en'
    keyboard = [
        [get_text(lang, 'btn_view_all_tickets'), get_text(lang, 'btn_view_pending_tickets'), get_text(lang, 'btn_view_closed_tickets')],
        [get_text(lang, 'admin_back')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if not tickets:
        text += f"No {filter_status} tickets found." if filter_status else "No tickets found."
    else:
        for t in tickets[:5]: # Show last 5
            status_icon = "🟢" if t['status'] == 'Open' else "🔴" if t['status'] == 'closed' else "🟡"
            text += f"{status_icon} #{t['id']}: {t['subject']} ({t['status']})\n"
    
    # Send text with inline buttons for viewing items
    item_keyboard = []
    if tickets:
        for t in tickets[:5]:
            item_keyboard.append([InlineKeyboardButton(f"View #{t['id']}", callback_data=f"admin_view_ticket:{t['id']}")])
    
    item_reply_markup = InlineKeyboardMarkup(item_keyboard) if item_keyboard else None

    if update.callback_query:
        if item_reply_markup:
            await update.callback_query.message.reply_text(text, reply_markup=item_reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.message.reply_text(text, parse_mode='Markdown')
        await update.callback_query.message.reply_text("👇 Options:", reply_markup=reply_markup)
    else:
        if item_reply_markup:
            await update.message.reply_text(text, reply_markup=item_reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
        await update.message.reply_text("👇 Options:", reply_markup=reply_markup)

async def admin_user_messages_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_user_messages(update, context, filter_status='all')

async def admin_user_messages_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_user_messages(update, context, filter_status='Pending')

async def admin_user_messages_closed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_user_messages(update, context, filter_status='closed')


async def admin_user_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays user management options."""
    if update.callback_query:
        await update.callback_query.answer()
        user = update.effective_user
    else:
        user = update.effective_user

    lang = get_user_lang(update, context) or 'en'

    if not await is_admin(user.username):
        return

    keyboard = [
        [get_text(lang, 'btn_list_users')],
        [get_text(lang, 'admin_back')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    msg = "👥 *User Management*\n\nSelect an option:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_list_users_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for listing users with persistent button handling."""
    if update.callback_query:
        await update.callback_query.answer()
        reply_method = update.callback_query.message.reply_text
    else:
        reply_method = update.message.reply_text

    users = database.get_recent_users(10)
    text = "*👥 User Management (Recent 10)*\nSelect a user to manage:\n\n"
    keyboard = []
    
    if users:
        for u in users:
            status_icon = "✅" if u['status'] == 'Approved' else "⏳" if u['status'] == 'Pending' else "❌"
            display_name = u['username'] if u['username'] else u['full_name']
            keyboard.append([InlineKeyboardButton(f"{status_icon} {display_name} ({u['status']})", callback_data=f"admin_manage_user:{u['id']}")])
    else:
        text += "No users found."
    
    # No back button needed in inline if we have persistent menu, or keep it for consistency
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await reply_method(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_manage_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays details and actions for a specific user."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.username):
        await query.message.reply_text("You are not authorized.")
        return

    try:
        data_parts = query.data.split(':')
        if data_parts[0] == 'admin_manage_user':
            user_id = int(data_parts[1])
        elif data_parts[0] == 'admin_act_user':
            # Format: admin_act_user:action:user_id
            user_id = int(data_parts[2])
        else:
             await query.message.reply_text("Invalid request data.")
             return
             
        user = database.get_customer(user_id)
        if not user:
            await query.message.reply_text("User not found.")
            return

        text = (
            f"👤 *User Details*\n\n"
            f"🆔 ID: {user['id']}\n"
            f"📛 Name: {user['full_name']}\n"
            f"🔗 Username: @{user['username']}\n"
            f"📞 Phone: {user['phone']}\n"
            f"📧 Email: {user['email']}\n"
            f"📍 Region: {user['region']}\n"
            f"🏷 Type: {user['customer_type']}\n"
            f"📊 Status: *{user['status']}*\n"
            f"👮 Admin: *{'Yes' if user['is_admin'] else 'No'}*"
        )
        
        keyboard = [
            [InlineKeyboardButton("� Ban (Reject)", callback_data=f"admin_act_user:reject:{user_id}"),
             InlineKeyboardButton("✅ Activate (Approve)", callback_data=f"admin_act_user:approve:{user_id}")],
            [InlineKeyboardButton("👮 Toggle Admin Status", callback_data=f"admin_act_user:toggle_admin:{user_id}")],
            [InlineKeyboardButton("⬅️ Back to List", callback_data='admin_user_management')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except (IndexError, ValueError):
        await query.message.reply_text("Invalid user selection.")

async def admin_user_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles ban/activate/toggle_admin actions."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.username):
        await query.message.reply_text("You are not authorized.")
        return
    data = query.data.split(':')
    action = data[1]
    user_id = int(data[2])
    
    # Get user details for protection check
    user = database.get_customer(user_id)
    
    # Protect superadmin (nexafinder) from ALL actions by other admins
    if user and user['username'] and user['username'].lower() == 'nexafinder':
        await query.answer("⛔ Cannot modify superadmin (nexafinder) account!", show_alert=True)
        return
    
    if action == 'reject':
        database.update_customer_status(user_id, 'Rejected')
        await query.message.reply_text("User has been banned/rejected.")
    elif action == 'approve':
        database.update_customer_status(user_id, 'Approved')
        await query.message.reply_text("User has been activated/approved.")
    elif action == 'toggle_admin':
        current_status = user['is_admin']
        new_status = 0 if current_status == 1 else 1
        
        database.set_admin_status(user['telegram_id'], new_status)
        status_str = "Admin" if new_status else "User"
        await query.message.reply_text(f"User is now a {status_str}.")
        
    # Refresh the view
    await admin_manage_user(update, context) # Re-render the user details with updated info

async def admin_reports_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays reports and logs menu."""
    if update.callback_query:
        await update.callback_query.answer()
        username = update.effective_user.username
        reply_method = update.callback_query.message.reply_text
    else:
        username = update.effective_user.username
        reply_method = update.message.reply_text

    lang = get_user_lang(update, context) or 'en'

    if not await is_admin(username):
        await reply_method("You are not authorized to access reports.")
        return

    # Fetching data
    total_revenue = database.get_total_revenue()
    total_users = database.get_total_users()
    total_orders = database.get_total_orders_count()
    total_tickets = database.get_total_tickets_count()
    
    text = (
        f"📈 *Reports & Logs*\n\n"
        f"💰 *Total Revenue:* ${total_revenue:,.2f}\n"
        f"🛒 *Total Orders:* {total_orders}\n"
        f"✉️ *Total Tickets:* {total_tickets}\n"
        f"👥 *Total Users:* {total_users}\n"
    )
    
    keyboard = [
        [get_text(lang, 'btn_export_orders')],
        [get_text(lang, 'admin_back')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await reply_method(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_export_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Placeholder for export logic since we don't have the full file
    # This was previously implemented or stubbed.
    await update.message.reply_text("📥 Exporting orders... (Feature to be implemented fully)")

async def admin_list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all products for management."""
    if update.callback_query:
        await update.callback_query.answer()
        user = update.effective_user
        reply_method = update.callback_query.message.reply_text
    else:
        user = update.effective_user
        reply_method = update.message.reply_text

    if not await is_admin(user.username):
        await reply_method("You are not authorized.")
        return

    try:
        products = database.get_all_products()
        if not products:
            await reply_method("No products found.")
            return

        text = "📋 *Product List*\n\n"
        for p in products:
            cat = p['category'] if 'category' in p.keys() and p['category'] else 'General'
            text += f"• {p['name']} - ${p['price']:.2f} (📁 {cat})\n"
        
        keyboard = []
        for p in products:
            keyboard.append([
                InlineKeyboardButton(f"✏️ Edit {p['name']}", callback_data=f"edit_prod:{p['id']}"),
                InlineKeyboardButton(f"🗑️ Delete", callback_data=f"admin_delete_product:{p['id']}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await reply_method(text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        await reply_method(f"❌ Error listing products: {e}\n\n`{tb}`", parse_mode='Markdown')

async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the add product conversation."""
    if update.callback_query:
        await update.callback_query.answer()
        reply_method = update.callback_query.message.reply_text
    else:
        reply_method = update.message.reply_text
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await reply_method("➕ *Add New Product*\n\nPlease enter the *Product Name*:", reply_markup=reply_markup, parse_mode='Markdown')
    return ADD_PRODUCT_NAME

async def receive_add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product_name'] = update.message.text
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please enter the *Product Description*:", reply_markup=reply_markup, parse_mode='Markdown')
    return ADD_PRODUCT_DESC

async def receive_add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product_desc'] = update.message.text
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please enter the *Price* (e.g., 1500.50):", reply_markup=reply_markup, parse_mode='Markdown')
    return ADD_PRODUCT_PRICE

async def receive_add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['new_product_price'] = price
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a number:")
        return ADD_PRODUCT_PRICE
        
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please enter the *Stock Quantity*:", reply_markup=reply_markup, parse_mode='Markdown')
    return ADD_PRODUCT_STOCK

async def receive_add_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("Invalid stock. Please enter a whole number:")
        return ADD_PRODUCT_STOCK
        
    context.user_data['new_product_stock'] = int(update.message.text)
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please enter *Available Quantities* (comma-separated, e.g., '1kg, 2kg, 5kg') or type 'None':", reply_markup=reply_markup, parse_mode='Markdown')
    return ADD_PRODUCT_QUANTITIES

async def receive_add_product_quantities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == 'none':
        context.user_data['new_product_quantities'] = None
    else:
        context.user_data['new_product_quantities'] = text

    # Get existing categories for suggestions
    categories = database.get_all_categories()
    category_text = ', '.join(categories) if categories else 'General'
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Please enter the *Product Category* (e.g., {category_text}) or type a new one:", reply_markup=reply_markup, parse_mode='Markdown')
    return ADD_PRODUCT_CATEGORY

async def receive_add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_product_category'] = text if text else 'General'

    keyboard = [[InlineKeyboardButton("Skip Image", callback_data='skip_image')], [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please upload a *Product Image* (optional) or click Skip:", reply_markup=reply_markup, parse_mode='Markdown')
    return ADD_PRODUCT_IMAGE

async def receive_add_product_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    ext = os.path.splitext(photo_file.file_path)[1] or ".jpg"
    
    upload_dir = os.path.join('uploads', 'products')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"prod_{uuid.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    await photo_file.download_to_drive(file_path)
    context.user_data['new_product_image'] = file_path
    
    await finalize_add_product(update, context)
    return ConversationHandler.END

async def skip_add_product_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['new_product_image'] = None
    
    await finalize_add_product(update, context)
    return ConversationHandler.END

async def finalize_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data['new_product_name']
    desc = context.user_data['new_product_desc']
    price = context.user_data['new_product_price']
    stock = context.user_data['new_product_stock']
    image = context.user_data['new_product_image']
    quantities = context.user_data.get('new_product_quantities')
    category = context.user_data.get('new_product_category', 'General')
    
    database.add_product(name, desc, price, stock, image, quantities, category)
    
    message = f"✅ *Product Added Successfully!*\n\n📁 Category: {category}\n🍯 Name: {name}\n💰 Price: ${price:.2f}\n📦 Stock: {stock}"
    if update.callback_query:
        await update.callback_query.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, parse_mode='Markdown')



async def admin_delete_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split(':')[1])
    database.delete_product(product_id)
    
    await query.message.reply_text("🗑 Product deleted.")
    await admin_list_products(update, context)

# --- Edit Product Handlers ---

async def start_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start edit product flow - show product list."""
    if update.callback_query:
        await update.callback_query.answer()
        user = update.effective_user
        reply_method = update.callback_query.message.reply_text
    else:
        user = update.effective_user
        reply_method = update.message.reply_text

    if not await is_admin(user.username):
        await reply_method("You are not authorized.")
        return ConversationHandler.END

    products = database.get_all_products()
    if not products:
        await reply_method("No products to edit.")
        return ConversationHandler.END

    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(f"✏️ {p['name']} - ${p['price']}", callback_data=f"edit_prod:{p['id']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await reply_method("✏️ *Edit Product*\n\nSelect a product to edit:", reply_markup=reply_markup, parse_mode='Markdown')
    return EDIT_PRODUCT_SELECT

async def select_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available fields to edit for selected product."""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split(':')[1])
    product = database.get_product(product_id)
    
    if not product:
        await query.message.reply_text("Product not found.")
        return ConversationHandler.END
    
    context.user_data['edit_product_id'] = product_id
    
    info = (
        f"✏️ *Editing: {product['name']}*\n\n"
        f"📁 Category: {product['category'] or 'General'}\n"
        f"📝 Description: {product['description'][:50]}...\n" if product['description'] and len(product['description']) > 50 else f"📝 Description: {product['description'] or 'None'}\n"
        f"💰 Price: ${product['price']:.2f}\n"
        f"📦 Stock: {product['stock']}\n"
        f"🖼 Image: {'Yes' if product['image_path'] else 'No'}\n\n"
        f"Select field to edit:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📝 Name", callback_data="field:name"), InlineKeyboardButton("📋 Description", callback_data="field:desc")],
        [InlineKeyboardButton("💰 Price", callback_data="field:price"), InlineKeyboardButton("📦 Stock", callback_data="field:stock")],
        [InlineKeyboardButton("📁 Category", callback_data="field:category"), InlineKeyboardButton("🖼 Image", callback_data="field:image")],
        [InlineKeyboardButton("⬅️ Back to Product List", callback_data="edit_back")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(info, reply_markup=reply_markup, parse_mode='Markdown')
    return EDIT_PRODUCT_FIELD

async def handle_edit_field_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle field selection and prompt for new value."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "edit_back":
        return await start_edit_product(update, context)
    
    field = query.data.split(':')[1]
    context.user_data['edit_field'] = field
    
    product_id = context.user_data['edit_product_id']
    product = database.get_product(product_id)
    
    prompts = {
        'name': f"Current name: *{product['name']}*\n\nEnter new name:",
        'desc': f"Current description: {product['description'] or 'None'}\n\nEnter new description:",
        'price': f"Current price: *${product['price']:.2f}*\n\nEnter new price:",
        'stock': f"Current stock: *{product['stock']}*\n\nEnter new stock quantity:",
        'category': f"Current category: *{product['category'] or 'General'}*\n\nEnter new category:",
        'image': "Upload a new product image:"
    }
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(prompts.get(field, "Enter new value:"), reply_markup=reply_markup, parse_mode='Markdown')
    
    if field == 'name':
        return EDIT_PRODUCT_NAME
    elif field == 'desc':
        return EDIT_PRODUCT_DESC
    elif field == 'price':
        return EDIT_PRODUCT_PRICE
    elif field == 'stock':
        return EDIT_PRODUCT_STOCK
    elif field == 'category':
        return EDIT_PRODUCT_FIELD  # Reuse for category text input
    elif field == 'image':
        return EDIT_PRODUCT_IMAGE
    
    return EDIT_PRODUCT_FIELD

async def receive_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update product name."""
    new_value = update.message.text
    product_id = context.user_data['edit_product_id']
    database.update_product(product_id, name=new_value)
    await update.message.reply_text(f"✅ Product name updated to: *{new_value}*", parse_mode='Markdown')
    return ConversationHandler.END

async def receive_edit_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update product description."""
    new_value = update.message.text
    product_id = context.user_data['edit_product_id']
    database.update_product(product_id, description=new_value)
    await update.message.reply_text("✅ Product description updated.", parse_mode='Markdown')
    return ConversationHandler.END

async def receive_edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update product price."""
    try:
        new_value = float(update.message.text)
        product_id = context.user_data['edit_product_id']
        database.update_product(product_id, price=new_value)
        await update.message.reply_text(f"✅ Product price updated to: *${new_value:.2f}*", parse_mode='Markdown')
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a number:")
        return EDIT_PRODUCT_PRICE

async def receive_edit_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update product stock."""
    if not update.message.text.isdigit():
        await update.message.reply_text("Invalid stock. Please enter a whole number:")
        return EDIT_PRODUCT_STOCK
    
    new_value = int(update.message.text)
    product_id = context.user_data['edit_product_id']
    database.update_product(product_id, stock=new_value)
    await update.message.reply_text(f"✅ Product stock updated to: *{new_value}*", parse_mode='Markdown')
    return ConversationHandler.END

async def receive_edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update product category."""
    new_value = update.message.text.strip()
    product_id = context.user_data['edit_product_id']
    
    database.update_product(product_id, category=new_value)
    
    await update.message.reply_text(f"✅ Product category updated to: *{new_value}*", parse_mode='Markdown')
    return ConversationHandler.END

async def receive_edit_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update product image."""
    photo_file = await update.message.photo[-1].get_file()
    ext = os.path.splitext(photo_file.file_path)[1] or ".jpg"
    
    upload_dir = os.path.join('uploads', 'products')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"prod_{uuid.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    await photo_file.download_to_drive(file_path)
    
    product_id = context.user_data['edit_product_id']
    database.update_product(product_id, image_path=file_path)
    
    await update.message.reply_text("✅ Product image updated.", parse_mode='Markdown')
    return ConversationHandler.END

async def user_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user messages outside of specific flows (checking for open tickets)."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Check for product search first
    if await handle_product_search(update, context):
        return
    
    # Check for open ticket
    ticket = database.get_active_ticket(user_id)
    
    if ticket:
        ticket_id = ticket['id']
        database.add_message(ticket_id, 'user', message_text)
        
        # Notify All Admins
        try:
            admin_message = (
                f"📩 *New Support Message*\n"
                f"Ticket: #{ticket_id}\n"
                f"User: {update.effective_user.full_name} (ID: {user_id})\n\n"
                f"{message_text}\n\n"
                f"👉 *Reply to this message to answer.*"
            )
            await notify_all_admins(context, admin_message)
        except Exception as e:
            logging.error(f"Failed to notify admin: {e}")
        
        await update.message.reply_text("✅ Message sent to support.")
    else:
        await unknown(update, context)

# --- Feedback Conversation Handlers ---

async def start_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_registration_status(update, context):
        return ConversationHandler.END
    """Starts the feedback process."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
    keyboard = [
        [InlineKeyboardButton("⭐ 1", callback_data='1'), InlineKeyboardButton("⭐ 2", callback_data='2'), InlineKeyboardButton("⭐ 3", callback_data='3')],
        [InlineKeyboardButton("⭐ 4", callback_data='4'), InlineKeyboardButton("⭐ 5", callback_data='5')]
    ]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "✍️ *We value your feedback!*\n\nPlease rate your experience with us:"
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    return RATING

async def receive_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores rating and asks for comment."""
    query = update.callback_query
    await query.answer()
    
    rating = int(query.data)
    context.user_data['feedback_rating'] = rating
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"You rated us {rating} stars! ⭐\n\nPlease write a brief comment or review:", reply_markup=reply_markup, parse_mode='Markdown')
    return COMMENT

async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores comment and asks for photo."""
    user_input = update.message.text
    if len(user_input) < 3:
        await update.message.reply_text("Comment is too short. Please write a bit more:")
        return COMMENT
        
    context.user_data['feedback_comment'] = user_input
    
    keyboard = [[InlineKeyboardButton("Skip Photo", callback_data='skip_photo')], [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Would you like to upload a photo? (Optional)\n\nSend a photo or click *Skip Photo*.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return PHOTO

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles photo upload."""
    user_id = update.effective_user.id
    rating = context.user_data['feedback_rating']
    comment = context.user_data['feedback_comment']

    # 1. Create a preliminary feedback entry to get an ID
    feedback_id = database.create_feedback(user_id, rating, comment)
    context.user_data['feedback_id'] = feedback_id  # Store for later use

    context.user_data['feedback_id'] = feedback_id

    if not update.message.photo:
        await update.message.reply_text("That doesn't look like a photo. Please send a photo or click *Skip Photo*.", parse_mode='Markdown')
        return PHOTO

    photo_file = await update.message.photo[-1].get_file()
    ext = os.path.splitext(photo_file.file_path)[1].lower() or ".jpg"

    if ext not in ALLOWED_EXTENSIONS:
        await update.message.reply_text(f"Unsupported file type: *{ext}*. Please send a photo with one of the allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}.", parse_mode='Markdown')
        return PHOTO

    # 2. Create structured uploads directory if not exists
    upload_dir = os.path.join('uploads', 'feedback')
    os.makedirs(upload_dir, exist_ok=True)

    # 3. Generate unique filename with feedback_id
    filename = f"{feedback_id}_{uuid.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, filename)

    await photo_file.download_to_drive(file_path)
    context.user_data['feedback_photo'] = file_path

    # 4. Update the feedback entry with the photo path
    database.update_feedback_photo_path(feedback_id, file_path)

    await show_feedback_confirmation(update, context)
    return CONFIRM_FEEDBACK

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles skipping photo."""
    query = update.callback_query
    await query.answer()
    context.user_data['feedback_photo'] = None
    
    # Create feedback entry (since photo was skipped, we create it here)
    user_id = update.effective_user.id
    rating = context.user_data['feedback_rating']
    comment = context.user_data['feedback_comment']
    feedback_id = database.create_feedback(user_id, rating, comment)
    context.user_data['feedback_id'] = feedback_id
    
    await show_feedback_confirmation(update, context)
    return CONFIRM_FEEDBACK

async def show_feedback_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows summary and confirmation buttons."""
    rating = context.user_data['feedback_rating']
    comment = context.user_data['feedback_comment']
    photo = context.user_data.get('feedback_photo')
    
    summary = (
        f"*Confirm Feedback:*\n\n"
        f"⭐ Rating: {rating}/5\n"
        f"📝 Comment: {comment}\n"
        f"🖼 Photo: {'Yes' if photo else 'No'}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Submit Feedback", callback_data='confirm_feedback'),
         InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')

async def confirm_feedback_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves feedback to DB and notifies admin."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel':
        await query.message.reply_text("Feedback cancelled.")
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    rating = context.user_data['feedback_rating']
    comment = context.user_data['feedback_comment']
    photo_path = context.user_data.get('feedback_photo')
    feedback_id = context.user_data['feedback_id'] # Retrieve the existing feedback_id

    # No need to call database.create_feedback here, as it was already created in receive_photo
    
    await query.message.reply_text("✅ Thank you for your feedback! It has been submitted for review.")
    
    # Notify All Admins
    try:
        message = (
            f"✍️ *New Feedback Received*\n\n"
            f"ID: #{feedback_id}\n"
            f"User ID: {user_id}\n"
            f"⭐ Rating: {rating}/5\n"
            f"📝 Comment: {comment}\n"
            f"🖼 Photo: {'Yes' if photo_path else 'No'}"
        )
        await notify_all_admins(context, message)
        
        if photo_path:
            for admin_id in database.get_all_admin_telegram_ids():
                try:
                    await context.bot.send_photo(chat_id=admin_id, photo=open(photo_path, 'rb'), caption=f"Photo for Feedback #{feedback_id}")
                except Exception as e:
                    logging.error(f"Failed to send photo to admin {admin_id}: {e}")
                    
    except Exception as e:
        logging.error(f"Failed to send admin notification for feedback: {e}")
            
    return ConversationHandler.END

# --- User Profile & History ---

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays user profile."""
    if not await check_registration_status(update, context):
        return

    user_id = update.effective_user.id
    customer = database.get_customer_by_telegram_id(user_id)
    
    message = (
        f"👤 *My Profile*\n\n"
        f"Name: {customer['full_name']}\n"
        f"Username: @{customer['username']}\n"
        f"Phone: {customer['phone']}\n"
        f"Email: {customer['email']}\n"
        f"Region: {customer['region']}\n"
        f"Type: {customer['customer_type']}\n"
        f"Status: {customer['status']}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 My Orders", callback_data='my_orders')],
        [InlineKeyboardButton("✉️ My Tickets", callback_data='my_tickets')],
        [InlineKeyboardButton("✍️ My Feedback", callback_data='my_feedback')],
        [InlineKeyboardButton("❌ Delete Account", callback_data='delete_account_init')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def my_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    # Need to implement get_orders_by_user in database.py
    orders = database.get_orders_by_user(user_id) 
    
    if not orders:
        await query.message.reply_text("You haven't placed any orders yet.")
        return

    text = "*🛒 My Orders*\n\n"
    for o in orders:
        text += f"🔹 Order #{o['id']}: {o['product_name']} (x{o['quantity']}) - {o['status']}\n"
        
    await query.message.reply_text(text, parse_mode='Markdown')

async def my_tickets_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    tickets = database.get_tickets_by_user(user_id)
    
    if not tickets:
        await query.message.reply_text("You haven't submitted any tickets yet.")
        return

    text = "*✉️ My Tickets*\nSelect a ticket to view details & replies:\n\n"
    keyboard = []
    
    for t in tickets:
        status_icon = "🟢" if t['status'] == 'Open' else "🟡" if t['status'] == 'Pending' else "🔴"
        keyboard.append([InlineKeyboardButton(f"{status_icon} #{t['id']}: {t['subject']}", callback_data=f"view_ticket:{t['id']}")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Back to Profile", callback_data='profile')])
    reply_markup = InlineKeyboardMarkup(keyboard)
        
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def view_ticket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    ticket_id = int(query.data.split(':')[1])
    ticket = database.get_ticket(ticket_id)
    
    if not ticket:
        await query.message.reply_text("Ticket not found.")
        return
        
    messages = database.get_ticket_messages(ticket_id)
    
    text = (
        f"🎫 *Ticket #{ticket['id']}*\n"
        f"Subject: {ticket['subject']}\n"
        f"Status: {ticket['status']}\n"
        f"Created: {ticket['created_at']}\n\n"
        f"*--- Conversation ---*\n"
    )
    
    for m in messages:
        sender = "👤 You" if m['sender_type'] == 'user' else "👨‍💼 Support"
        text += f"\n*{sender}:* {m['message']}\n"
        
    text += "\n\n_To reply, simply type your message here (if ticket is active)._"
    
    keyboard = [[InlineKeyboardButton("⬅️ Back to My Tickets", callback_data='my_tickets')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def my_feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    # Need to implement get_feedback_by_user in database.py
    feedbacks = database.get_feedback_by_user(user_id)
    
    if not feedbacks:
        await query.message.reply_text("You haven't submitted any feedback yet.")
        return

    text = "*✍️ My Feedback*\n\n"
    for f in feedbacks:
        text += f"🔹 {f['rating']}⭐: {f['comment']} - {f['status']}\n"
        
    await query.message.reply_text(text, parse_mode='Markdown')

# --- Order Conversation Handlers ---

async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_registration_status(update, context):
        return ConversationHandler.END
    """Starts the order process."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # Check if triggered by "Order This Product" from catalog
        if query.data.startswith('order_product:'):
            product_id = int(query.data.split(':')[1])
            product = database.get_product(product_id)
            
            if product:
                context.user_data['order_product'] = product['name']
                context.user_data['order_product_price'] = product['price']
                
                # Check for available quantities
                if product['available_quantities']:
                    quantities = [q.strip() for q in product['available_quantities'].split(',')]
                    keyboard = []
                    row = []
                    for q in quantities:
                        row.append(InlineKeyboardButton(q, callback_data=f"qty:{q}"))
                        if len(row) == 2:
                            keyboard.append(row)
                            row = []
                    if row:
                        keyboard.append(row)
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text(f"🛒 *Ordering: {product['name']}*\n\nPlease select a quantity:", reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await query.message.reply_text(f"🛒 *Ordering: {product['name']}*\n\nHow many would you like to order? (Please enter a number):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]), parse_mode='Markdown')
                
                return QUANTITY

    # Fetch products from DB
    products = database.get_all_products()
    
    if products:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="🛒 *New Order*\n\nPlease select a product from our catalog:", parse_mode='Markdown')
        
        for p in products:
            keyboard = [[InlineKeyboardButton(f"Select {p['name']} - ${p['price']}", callback_data=f"prod:{p['id']}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            caption = f"*{p['name']}*\n{p['description']}\nPrice: ${p['price']}\nStock: {p['stock']}"
            
            if p['image_path'] and os.path.exists(p['image_path']):
                try:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id, 
                        photo=open(p['image_path'], 'rb'), 
                        caption=caption, 
                        reply_markup=reply_markup, 
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.error(f"Failed to send image for product {p['id']}: {e}")
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id, 
                        text=caption, 
                        reply_markup=reply_markup, 
                        parse_mode='Markdown'
                    )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=caption, 
                    reply_markup=reply_markup, 
                    parse_mode='Markdown'
                )
                
        # Add a Cancel button at the end
        cancel_keyboard = [[InlineKeyboardButton("❌ Cancel Order", callback_data='cancel')]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="End of Catalog", reply_markup=InlineKeyboardMarkup(cancel_keyboard))
        
        return PRODUCT_NAME
    else:
        # Fallback to manual entry if no products in DB
        # Fallback to manual entry if no products in DB
        text = "🛒 *New Order*\n\nPlease enter the *Product Name* you would like to order:"
        keyboard = [[InlineKeyboardButton("❌ Cancel Order", callback_data='cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return PRODUCT_NAME

async def receive_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores product name and asks for quantity."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data.startswith('prod:'):
            product_id = int(data.split(':')[1])
            product = database.get_product(product_id)
            if product:
                context.user_data['order_product'] = product['name']
                context.user_data['order_product_price'] = product['price'] # Store price for later maybe
                
                # Check for available quantities
                if product['available_quantities']:
                    quantities = [q.strip() for q in product['available_quantities'].split(',')]
                    keyboard = []
                    row = []
                    for q in quantities:
                        row.append(InlineKeyboardButton(q, callback_data=f"qty:{q}"))
                        if len(row) == 2:
                            keyboard.append(row)
                            row = []
                    if row:
                        keyboard.append(row)
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text(f"You selected: *{product['name']}*.\n\nPlease select a quantity:", reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await query.message.reply_text(f"You selected: *{product['name']}*.\n\nHow many would you like to order? (Please enter a number):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]), parse_mode='Markdown')
                
                return QUANTITY
            else:
                 await query.message.reply_text("Product not found. Please select again.")
                 return PRODUCT_NAME
    
    user_input = update.message.text
    if len(user_input) < 2:
        await update.message.reply_text("Product name is too short. Please enter the product name:")
        return PRODUCT_NAME
        
    context.user_data['order_product'] = user_input
    await update.message.reply_text("How many would you like to order? (Please enter a number):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]))
    return QUANTITY

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores quantity and asks for delivery address."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data.startswith('qty:'):
            quantity = query.data.split(':')[1]
            # Try to convert to int if possible, otherwise keep as string (e.g. "1kg")
            # For simplicity, we treat it as the quantity string
            context.user_data['order_quantity'] = quantity
            await query.message.reply_text(f"Quantity selected: {quantity}\n\nPlease enter your *Delivery Address*:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]), parse_mode='Markdown')
            return DELIVERY_ADDRESS

    user_input = update.message.text
    if not user_input.isdigit() or int(user_input) <= 0:
        await update.message.reply_text("Please enter a valid quantity (positive number):")
        return QUANTITY
        
    context.user_data['order_quantity'] = int(user_input)
    await update.message.reply_text("Please enter your *Delivery Address*:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]), parse_mode='Markdown')
    return DELIVERY_ADDRESS

async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores address and asks for payment type."""
    user_input = update.message.text
    if len(user_input) < 5:
        await update.message.reply_text("Address seems too short. Please enter your full delivery address:")
        return DELIVERY_ADDRESS
        
    context.user_data['order_address'] = user_input
    
    keyboard = [
        [InlineKeyboardButton("Cash on Delivery", callback_data='Cash'),
         InlineKeyboardButton("Bank Transfer", callback_data='Transfer')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please select a *Payment Method*:", reply_markup=reply_markup, parse_mode='Markdown')
    return PAYMENT_TYPE

async def receive_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores payment type and asks for confirmation."""
    query = update.callback_query
    await query.answer()
    context.user_data['order_payment'] = query.data
    
    # Summary
    summary = (
        f"*Confirm Order Details:*\n\n"
        f"🍯 Product: {context.user_data['order_product']}\n"
        f"🔢 Quantity: {context.user_data['order_quantity']}\n"
        f"📍 Address: {context.user_data['order_address']}\n"
        f"💳 Payment: {context.user_data['order_payment']}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Order", callback_data='confirm_order'),
         InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    return CONFIRM_ORDER

async def confirm_order_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves order to DB and notifies admin."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel':
        await query.message.reply_text("Order cancelled.")
        return ConversationHandler.END
    
    # Save to DB
    user_id = update.effective_user.id
    product = context.user_data['order_product']
    quantity = context.user_data['order_quantity']
    address = context.user_data['order_address']
    payment = context.user_data['order_payment']
    price = context.user_data.get('order_product_price', 0)
    
    order_id = database.create_order(user_id, product, quantity, address, payment, price)
    
    await query.message.reply_text(f"✅ Order #{order_id} submitted successfully! We will process it shortly.")
    
    # Notify Admin
    admin_id = os.getenv("ADMIN_ID")
    # Notify All Admins about new order
    message = (
        f"🛒 *New Order Received*\n\n"
        f"Order ID: #{order_id}\n"
        f"User ID: {user_id}\n"
        f"Product: {product}\n"
        f"Quantity: {quantity}\n"
        f"Address: {address}\n"
        f"Payment: {payment}\n"
        f"Price: ${price:.2f}"
    )
    keyboard = [
        [InlineKeyboardButton("Approve", callback_data=f"admin:approve:orders:{order_id}"),
         InlineKeyboardButton("Reject", callback_data=f"admin:reject:orders:{order_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await notify_all_admins(context, message, reply_markup=reply_markup)
            
    return ConversationHandler.END

async def set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.username):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setadmin <telegram_id>")
        return

    target_telegram_id = int(context.args[0])
    database.set_admin_status(target_telegram_id, 1)
    await update.message.reply_text(f"User {target_telegram_id} has been set as admin.")

async def set_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.username):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setuser <telegram_id>")
        return

    target_telegram_id = int(context.args[0])
    
    # Check if target is the superadmin (nexafinder)
    target_user = database.get_customer_by_telegram_id(target_telegram_id)
    if target_user and target_user['username'] and target_user['username'].lower() == 'nexafinder':
        await update.message.reply_text("⛔ Cannot remove admin privileges from the superadmin (nexafinder)!")
        return
    
    database.set_admin_status(target_telegram_id, 0)
    await update.message.reply_text(f"User {target_telegram_id} has been removed from admin.")

async def order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /order command."""
    await update.message.reply_text("You selected: Make Order (Placeholder)")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the help command."""
    lang = get_user_lang(update, context) or 'en'
    text = get_text(lang, 'help_text')
    await update.message.reply_text(text, parse_mode='Markdown')


async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show product catalog with categories, search, and sorting options."""
    if not await check_registration_status(update, context):
        return
    
    lang = get_user_lang(update, context) or 'en'
    
    # Get categories for filter buttons
    categories = database.get_all_categories()
    
    # Build category buttons (2 per row)
    keyboard = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat:{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Add search and sort options
    keyboard.append([InlineKeyboardButton("🔍 Search Products", callback_data="search_products")])
    keyboard.append([
        InlineKeyboardButton("💰 Sort by Price", callback_data="sort:price:asc"),
        InlineKeyboardButton("🔤 Sort by Name", callback_data="sort:name:asc")
    ])
    keyboard.append([InlineKeyboardButton("📋 View All Products", callback_data="cat:all")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "📚 *Product Catalog*\n\nBrowse by category, search, or view all:"
    
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        except:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def browse_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show products filtered by category."""
    query = update.callback_query
    await query.answer()
    
    category = query.data.split(':')[1]
    
    if category == 'all':
        products = database.get_products_available()
        title = "📋 *All Products*"
    else:
        products = database.get_products_by_category(category)
        title = f"📁 *{category}*"
    
    if not products:
        keyboard = [[InlineKeyboardButton("⬅️ Back to Catalog", callback_data="browse_catalog")]]
        await query.message.edit_text(f"{title}\n\nNo products found in this category.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    keyboard = []
    for p in products:
        btn_text = f"🍯 {p['name']} - ${p['price']:.2f}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_product:{p['id']}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Catalog", callback_data="browse_catalog")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"{title}\n\nSelect a product:", reply_markup=reply_markup, parse_mode='Markdown')

async def sort_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show products sorted by specified field."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(':')
    sort_by = parts[1]
    sort_order = parts[2] if len(parts) > 2 else 'asc'
    
    products = database.search_products_advanced(sort_by=sort_by, sort_order=sort_order)
    
    sort_label = "Price ↑" if sort_by == 'price' and sort_order == 'asc' else \
                 "Price ↓" if sort_by == 'price' else \
                 "Name A-Z" if sort_by == 'name' and sort_order == 'asc' else "Name Z-A"
    
    if not products:
        keyboard = [[InlineKeyboardButton("⬅️ Back to Catalog", callback_data="browse_catalog")]]
        await query.message.edit_text("No products found.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    keyboard = []
    for p in products:
        btn_text = f"🍯 {p['name']} - ${p['price']:.2f}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_product:{p['id']}")])
    
    # Toggle sort order buttons
    new_order = 'desc' if sort_order == 'asc' else 'asc'
    keyboard.append([
        InlineKeyboardButton(f"🔄 Reverse Order", callback_data=f"sort:{sort_by}:{new_order}")
    ])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Catalog", callback_data="browse_catalog")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"📋 *Products (Sorted: {sort_label})*\n\nSelect a product:", reply_markup=reply_markup, parse_mode='Markdown')

async def start_product_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate product search."""
    query = update.callback_query
    await query.answer()
    
    context.user_data['awaiting_search'] = True
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="browse_catalog")]]
    await query.message.edit_text("🔍 *Search Products*\n\nType your search query (product name or description):", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_product_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product search input."""
    if not context.user_data.get('awaiting_search'):
        return False
    
    context.user_data['awaiting_search'] = False
    query_text = update.message.text
    
    products = database.search_products(query_text)
    
    if not products:
        keyboard = [[InlineKeyboardButton("🔍 Search Again", callback_data="search_products")],
                    [InlineKeyboardButton("⬅️ Back to Catalog", callback_data="browse_catalog")]]
        await update.message.reply_text(f"No products found matching '{query_text}'.", reply_markup=InlineKeyboardMarkup(keyboard))
        return True
    
    keyboard = []
    for p in products:
        btn_text = f"🍯 {p['name']} - ${p['price']:.2f}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_product:{p['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔍 Search Again", callback_data="search_products")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Catalog", callback_data="browse_catalog")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"🔍 *Search Results for '{query_text}'*\n\nFound {len(products)} product(s):", reply_markup=reply_markup, parse_mode='Markdown')
    return True

async def view_product_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed product information."""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split(':')[1])
    product = database.get_product(product_id)
    
    if not product:
        await query.message.reply_text("Product not found.")
        return
    
    lang = get_user_lang(update, context) or 'en'
    
    text = (
        f"**{product['name']}**\n\n"
        f"{product['description'] or 'No description available.'}\n\n"
        f"💰 *Price:* ${product['price']:.2f}\n"
        f"📦 *In Stock:* {product['stock']} units"
    )
    
    keyboard = []
    if product['stock'] > 0:
        keyboard.append([InlineKeyboardButton("🛒 Order This Product", callback_data=f"order_product:{product_id}")])
    else:
        keyboard.append([InlineKeyboardButton("❌ Out of Stock", callback_data="no_action")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Catalog", callback_data="browse_catalog")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if product['image_path']:
        try:
            await query.message.reply_photo(
                photo=open(product['image_path'], 'rb'),
                caption=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        except Exception as e:
            logging.error(f"Failed to send product image: {e}")
    
    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def blog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the blog button."""
    await update.message.reply_text("📰 *GPBlog*\n\nVisit our blog at: https://example.com/blog", parse_mode='Markdown')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder callback handler for main menu buttons."""
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    
    # Note: 'register' is handled by the ConversationHandler entry point
    if choice == 'order':
        await start_order(update, context)
    elif choice == 'feedback':
        await start_feedback(update, context)
    elif choice == 'complaint' or choice == 'inquiry' or choice == 'contact_support':
        await start_support(update, context)
    elif choice == 'help':
        await help_command(update, context)

async def start_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the persistent main menu options."""
    lang = get_user_lang(update, context) or 'en'
    
    keyboard = [
        [get_text(lang, 'order'), get_text(lang, 'feedback')],
        ['📚 Browse Products', get_text(lang, 'profile')],
        [get_text(lang, 'complaint'), get_text(lang, 'inquiry')],
        [get_text(lang, 'back_button')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    msg = "Please select an option:"
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=reply_markup)

async def back_to_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Returns to the top-level menu."""
    await start(update, context)



async def admin_set_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows options to set another user as admin."""
    query = update.callback_query
    await query.answer()
    
    # Simple instruction for now, or could be a conversation
    await query.message.reply_text("To set an admin, please use the command:\n/setadmin <username>\n\nExample: /setadmin johndoe")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback for unknown messages."""
    await update.message.reply_text("Sorry, I didn't understand that command or message. Type /start to see the menu.")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token or token == "your_bot_token_here":
        print("Error: BOT_TOKEN is not set in .env file.")
        return

    application = ApplicationBuilder().token(token).post_init(post_init).build()
    
    # Common Navigation Handlers for Fallbacks
    navigation_handlers = [
        CommandHandler('cancel', cancel),
        CallbackQueryHandler(cancel, pattern='^cancel$'),
        MessageHandler(filters.Regex(MENU_PATTERN), start_main_menu),
        MessageHandler(filters.Regex(ADMIN_PATTERN), admin_button_handler),
        MessageHandler(filters.Regex(ADMIN_DASHBOARD_PATTERN), admin_dashboard_text_handler),
        MessageHandler(filters.Regex(ADMIN_DASHBOARD_OVERVIEW_PATTERN), admin_dashboard_overview),
        MessageHandler(filters.Regex(ADMIN_MANAGE_PRODUCTS_PATTERN), admin_products_menu),
        MessageHandler(filters.Regex(ADMIN_USER_MESSAGES_PATTERN), admin_user_messages),
        MessageHandler(filters.Regex(ADMIN_USER_MANAGEMENT_PATTERN), admin_user_management_menu),
        MessageHandler(filters.Regex(ADMIN_REPORTS_LOGS_PATTERN), admin_reports_logs),
        MessageHandler(filters.Regex(ADMIN_BACK_PATTERN), admin_button_handler),
        MessageHandler(filters.Regex(ADMIN_ADD_PRODUCT_PATTERN), start_add_product), # Direct link to conversation
        MessageHandler(filters.Regex(ADMIN_LIST_PRODUCTS_PATTERN), admin_list_products),
        MessageHandler(filters.Regex(ADMIN_LIST_USERS_PATTERN), admin_list_users_manage), # Assuming this callback exists or need a wrapper
        MessageHandler(filters.Regex(ADMIN_EXPORT_ORDERS_PATTERN), admin_export_orders), # Direct link to function
        MessageHandler(filters.Regex(ADMIN_VIEW_ALL_TICKETS_PATTERN), admin_user_messages_all),
        MessageHandler(filters.Regex(ADMIN_VIEW_PENDING_TICKETS_PATTERN), admin_user_messages_pending),
        MessageHandler(filters.Regex(ADMIN_VIEW_CLOSED_TICKETS_PATTERN), admin_user_messages_closed),
    ]

    # Registration Conversation Handler
    registration_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_registration, pattern='^register$'),
            CommandHandler('register', start_registration),
            MessageHandler(filters.Regex(REGISTER_PATTERN), start_registration)
        ],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_full_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
            REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_region)],
            CUSTOMER_TYPE: [CallbackQueryHandler(receive_customer_type, pattern='^(New|Returning)$')],
            CONFIRMATION: [CallbackQueryHandler(confirm_registration, pattern='^(confirm|cancel)$')],
            RETURNING_USER_OPTIONS: [
                CallbackQueryHandler(handle_returning_user_choice, pattern='^(reactivate_account|register_new_account)$')
            ],
        },
        fallbacks=navigation_handlers,
    )

    # Support Conversation Handler
    support_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_support, pattern='^(Inquiry|Complaint|contact_support)$'),
            CommandHandler('support', start_support),
            CommandHandler('complaint', start_support),
            CommandHandler('inquiry', start_support),
            MessageHandler(filters.Regex(SUPPORT_PATTERN), start_support)
        ],
        states={
            TICKET_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ticket_subject)],
            TICKET_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ticket_message)],
            TICKET_ATTACHMENT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_ticket_attachment),
                CallbackQueryHandler(skip_ticket_attachment, pattern='^skip_attachment$')
            ],
            CONFIRM_TICKET: [CallbackQueryHandler(confirm_ticket_submission, pattern='^(confirm_ticket|cancel)$')]
        },
        fallbacks=navigation_handlers,
    )

    # Feedback Conversation Handler
    feedback_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_feedback, pattern='^feedback$'),
            # No command for feedback initially requested, but can add one if needed
            MessageHandler(filters.Regex(FEEDBACK_PATTERN), start_feedback)
        ],
        states={
            RATING: [CallbackQueryHandler(receive_rating, pattern='^[1-5]$')],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment)],

            PHOTO: [
                MessageHandler(filters.PHOTO, receive_photo),
                CallbackQueryHandler(skip_photo, pattern='^skip_photo$')
            ],
            CONFIRM_FEEDBACK: [CallbackQueryHandler(confirm_feedback_submission, pattern='^(confirm_feedback|cancel)$')],
        },
        fallbacks=navigation_handlers,
    )

    # Order Conversation Handler
    order_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_order, pattern='^order$'),
            CallbackQueryHandler(start_order, pattern='^order_product:\\d+$'),
            CommandHandler('order', start_order),
            MessageHandler(filters.Regex(ORDER_PATTERN), start_order)
        ],
        states={
            PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_product),
                CallbackQueryHandler(receive_product, pattern='^prod:\\d+$')
            ],
            QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity),
                CallbackQueryHandler(receive_quantity, pattern='^qty:.+$')
            ],
            DELIVERY_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address)],
            PAYMENT_TYPE: [CallbackQueryHandler(receive_payment, pattern='^(Cash|Transfer)$')],
            CONFIRM_ORDER: [CallbackQueryHandler(confirm_order_submission, pattern='^(confirm_order|cancel)$')],
        },
        fallbacks=navigation_handlers,
    )

    # Add Product Conversation Handler
    add_product_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_product, pattern='^admin_add_product$'),
            MessageHandler(filters.Regex(ADMIN_ADD_PRODUCT_PATTERN), start_add_product)
        ],
        states={
            ADD_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_name)],
            ADD_PRODUCT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_desc)],
            ADD_PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_price)],
            ADD_PRODUCT_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_stock)],
            ADD_PRODUCT_QUANTITIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_quantities)],
            ADD_PRODUCT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_category)],
            ADD_PRODUCT_IMAGE: [
                MessageHandler(filters.PHOTO, receive_add_product_image),
                CallbackQueryHandler(skip_add_product_image, pattern='^skip_image$')
            ],
        },
        fallbacks=navigation_handlers,
    )

    # Add Handlers
    application.add_handler(registration_handler)
    application.add_handler(order_handler)
    application.add_handler(support_handler)
    application.add_handler(feedback_handler)
    application.add_handler(add_product_handler)
    
    # Edit Product Conversation Handler
    edit_product_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(select_edit_field, pattern='^edit_prod:\\d+$'),
        ],
        states={
            EDIT_PRODUCT_SELECT: [CallbackQueryHandler(select_edit_field, pattern='^edit_prod:\\d+$')],
            EDIT_PRODUCT_FIELD: [
                CallbackQueryHandler(handle_edit_field_selection, pattern='^field:.+$'),
                CallbackQueryHandler(start_edit_product, pattern='^edit_back$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_category),  # For category input
            ],
            EDIT_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_name)],
            EDIT_PRODUCT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_desc)],
            EDIT_PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_price)],
            EDIT_PRODUCT_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_stock)],
            EDIT_PRODUCT_IMAGE: [MessageHandler(filters.PHOTO, receive_edit_image)],
        },
        fallbacks=navigation_handlers,
    )
    application.add_handler(edit_product_handler)
    
    application.add_handler(CallbackQueryHandler(admin_view_ticket, pattern='^admin_view_ticket:\\d+$'))
    application.add_handler(CallbackQueryHandler(admin_products_menu, pattern='^admin_products$'))
    application.add_handler(CallbackQueryHandler(admin_list_products, pattern='^admin_list_products$'))
    application.add_handler(CallbackQueryHandler(admin_delete_product_handler, pattern='^admin_delete_product:\\d+$'))
    application.add_handler(CallbackQueryHandler(admin_user_messages, pattern='^admin_user_messages(:.+)?$'))
    application.add_handler(CallbackQueryHandler(admin_dashboard_overview, pattern='^admin_dashboard_overview$'))
    application.add_handler(CallbackQueryHandler(admin_user_management_menu, pattern='^admin_user_management$'))
    application.add_handler(CallbackQueryHandler(admin_reports_logs, pattern='^admin_reports_logs$'))
    application.add_handler(CallbackQueryHandler(admin_menu, pattern='^admin$'))
    application.add_handler(CallbackQueryHandler(admin_set_admin_menu, pattern='^admin_set_admin_menu$'))
    
    # Newly added admin handlers
    application.add_handler(CallbackQueryHandler(admin_manage_user, pattern='^admin_manage_user:\\d+$'))
    application.add_handler(CallbackQueryHandler(admin_user_action_handler, pattern='^admin_act_user:.+$'))
    # application.add_handler(CallbackQueryHandler(admin_reply_to_ticket_callback, pattern='^admin_reply_to_ticket:\\d+$')) # Replaced by ConversationHandler
    application.add_handler(CallbackQueryHandler(admin_resolve_ticket_callback, pattern='^admin_resolve_ticket:\\d+$'))
    
    # Admin Reply Conversation Handler
    admin_reply_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_reply_to_ticket_start, pattern='^admin_reply_to_ticket:\\d+$')],
        states={
            ADMIN_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_reply)]
        },
        fallbacks=navigation_handlers,
    )
    application.add_handler(admin_reply_conv_handler)
    
    # User Profile Handlers
    application.add_handler(CommandHandler('profile', profile_command))
    application.add_handler(CallbackQueryHandler(profile_command, pattern='^profile$'))
    application.add_handler(CallbackQueryHandler(my_orders_callback, pattern='^my_orders$'))
    application.add_handler(CallbackQueryHandler(my_tickets_callback, pattern='^my_tickets$'))
    application.add_handler(CallbackQueryHandler(view_ticket_callback, pattern='^view_ticket:\\d+$'))
    application.add_handler(CallbackQueryHandler(my_feedback_callback, pattern='^my_feedback$'))

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('menu', start))
    application.add_handler(CommandHandler('admin', admin_menu))
    application.add_handler(CommandHandler("feedback", start_feedback))
    application.add_handler(CommandHandler("setadmin", setadmin))

    application.add_handler(CommandHandler("setuser", set_user))
    application.add_handler(CommandHandler('help', help_command))
    
    # Product Catalog Handlers
    application.add_handler(MessageHandler(filters.Regex('📚.*Products'), browse_products))
    application.add_handler(CallbackQueryHandler(browse_products, pattern='^browse_catalog$'))
    application.add_handler(CallbackQueryHandler(view_product_details, pattern='^view_product:\\d+$'))
    application.add_handler(CallbackQueryHandler(browse_by_category, pattern='^cat:.+$'))
    application.add_handler(CallbackQueryHandler(sort_products, pattern='^sort:.+$'))
    application.add_handler(CallbackQueryHandler(start_product_search, pattern='^search_products$'))
    
    # Button Handlers
    application.add_handler(MessageHandler(filters.Regex(PROFILE_PATTERN), profile_command))
    application.add_handler(MessageHandler(filters.Regex(HELP_PATTERN), help_command))
    application.add_handler(MessageHandler(filters.Regex(BLOG_PATTERN), blog_command))
    application.add_handler(MessageHandler(filters.Regex(MENU_PATTERN), start_main_menu))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_PATTERN), admin_button_handler))
    application.add_handler(MessageHandler(filters.Regex(BACK_PATTERN), back_to_home))
    application.add_handler(MessageHandler(filters.Regex(COMPLAINT_PATTERN), start_support))
    application.add_handler(MessageHandler(filters.Regex(INQUIRY_PATTERN), start_support))
    # application.add_handler(MessageHandler(filters.Regex(LANGUAGE_PATTERN), choose_language)) # Handled below

    application.add_handler(MessageHandler(filters.Regex(LANGUAGE_PATTERN), choose_language))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_DASHBOARD_PATTERN), admin_dashboard_text_handler))
    application.add_handler(MessageHandler(filters.Regex(ADD_ADMIN_PATTERN), admin_add_admin_text_handler))
    
    application.add_handler(MessageHandler(filters.Regex(ADMIN_DASHBOARD_OVERVIEW_PATTERN), admin_dashboard_overview))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_MANAGE_PRODUCTS_PATTERN), admin_products_menu))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_USER_MESSAGES_PATTERN), admin_user_messages))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_USER_MANAGEMENT_PATTERN), admin_user_management_menu))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_REPORTS_LOGS_PATTERN), admin_reports_logs))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_BACK_PATTERN), admin_button_handler))

    application.add_handler(CallbackQueryHandler(promote_admin_callback, pattern='^promote_admin:\\d+$'))

    application.add_handler(CallbackQueryHandler(admin_action_handler, pattern='^admin:'))
    # Add    # Delete Account Conversation
    delete_account_handler = ConversationHandler(
        entry_points=[
            CommandHandler('deleteaccount', start_delete_account),
            CallbackQueryHandler(start_delete_account, pattern='^delete_account_init$')
        ],
        states={
            CONFIRM_DELETE: [CallbackQueryHandler(confirm_delete_account, pattern='^(confirm_delete|cancel_delete)$')]
        },
        fallbacks=[CommandHandler('cancel', cancel), CallbackQueryHandler(cancel, pattern='^cancel$')],
    )
    application.add_handler(delete_account_handler)
    
    # Language and other global callbacks
    application.add_handler(CallbackQueryHandler(set_language, pattern='^lang_'))
    application.add_handler(CallbackQueryHandler(order_later_callback, pattern='^order_later$'))

    application.add_handler(CallbackQueryHandler(button_handler)) # For other menu buttons

    # Admin Reply Handler (Must be before general fallback)
    # Missing Admin Sub-menu Handlers
    # application.add_handler(MessageHandler(filters.Regex(ADMIN_ADD_PRODUCT_PATTERN), start_add_product)) # Handled in Conversation
    application.add_handler(MessageHandler(filters.Regex(ADMIN_LIST_PRODUCTS_PATTERN), admin_list_products))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_LIST_USERS_PATTERN), admin_list_users_manage))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_EXPORT_ORDERS_PATTERN), admin_export_orders))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_VIEW_ALL_TICKETS_PATTERN), admin_user_messages_all))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_VIEW_PENDING_TICKETS_PATTERN), admin_user_messages_pending))
    application.add_handler(MessageHandler(filters.Regex(ADMIN_VIEW_CLOSED_TICKETS_PATTERN), admin_user_messages_closed))

    # Using filters.REPLY to catch replies
    application.add_handler(MessageHandler(filters.REPLY, admin_reply_handler))
    
    # General User Message Handler (for continuing open tickets or fallback)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_reply_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
