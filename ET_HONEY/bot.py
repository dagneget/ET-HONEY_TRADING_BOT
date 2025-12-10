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
import re
import uuid

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx', '.txt'}

# Load environment variables
load_dotenv()

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
ADD_PRODUCT_NAME, ADD_PRODUCT_DESC, ADD_PRODUCT_PRICE, ADD_PRODUCT_STOCK, ADD_PRODUCT_IMAGE = range(80, 85)

async def post_init(application: Application):
    """Sets the bot's menu button commands."""
    commands = [
        BotCommand("start", "Open Main Menu"),
        BotCommand("register", "Register as Customer"),
        BotCommand("order", "Make an Order"),
        BotCommand("feedback", "Give Feedback"),
        BotCommand("complaint", "File a Complaint"),
        BotCommand("inquiry", "Make an Inquiry"),
        BotCommand("about", "About Us"),
        BotCommand("deleteaccount", "Delete My Account"),
        BotCommand("admin", "Admin Dashboard"),
        BotCommand("setadmin", "Set User as Admin (Temporary)"),
    ]
    await application.bot.set_my_commands(commands)

async def admin_dashboard_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays an overview of the bot's statistics for admins."""
    query = update.callback_query
    await query.answer()
    username = query.from_user.username
    if not await is_admin(username):
        await query.message.reply_text("You are not authorized to access the admin dashboard.")
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
        f"🚨 System Alerts: {system_alerts}"
    )

    keyboard = [
        [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data='admin')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(text=message, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays a list of user messages/tickets for admins with filtering options."""
    query = update.callback_query
    await query.answer()
    username = query.from_user.username
    if not await is_admin(username):
        await query.message.reply_text("You are not authorized to access this feature.")
        return

    data_parts = query.data.split(':')
    filter_status = data_parts[1] if len(data_parts) > 1 else None

    tickets = database.get_all_tickets(filter_status)

    if not tickets:
        message = f"No {filter_status.lower()} user messages found." if filter_status else "No user messages found."
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data='admin')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(text=message, reply_markup=reply_markup)
        return

    message_text = "*✉️ User Messages*\n\n"
    keyboard_buttons = []
    for ticket in tickets:
        customer = database.get_customer(ticket['user_id'])
        username = customer['username'] if customer else "Unknown User"
        message_text += f"ID: {ticket['id']} | User: @{username} | Subject: {ticket['subject']} | Status: {ticket['status']}\n"
        keyboard_buttons.append([InlineKeyboardButton(f"View Ticket {ticket['id']}", callback_data=f'admin_view_ticket:{ticket['id']}')])

    filter_keyboard = [
        InlineKeyboardButton("All", callback_data='admin_user_messages'),
        InlineKeyboardButton("Pending", callback_data='admin_user_messages:Pending'),
        InlineKeyboardButton("Closed", callback_data='admin_user_messages:closed'),
    ]
    keyboard_buttons.insert(0, filter_keyboard)
    keyboard_buttons.append([InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data='admin')])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)

    await query.message.reply_text(text=message_text, reply_markup=reply_markup, parse_mode='Markdown')

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
    customer = database.get_customer(ticket['user_id'])
    username = customer['username'] if customer else "Unknown User"

    message_text = f"*✉️ Ticket #{ticket_id} with @{username} (Status: {ticket['status']})*\n\n"
    for msg in messages:
        message_text += f"*{msg['sender_type'].capitalize()}*: {msg['message']}\n"

    context.user_data['admin_reply_ticket_id'] = ticket_id
    keyboard = [
        [InlineKeyboardButton("↩️ Reply", callback_data=f'admin_reply_to_ticket:{ticket_id}')],
        [InlineKeyboardButton("✅ Resolve Ticket", callback_data=f'admin_resolve_ticket:{ticket_id}')],
        [InlineKeyboardButton("⬅️ Back to Messages", callback_data='admin_user_messages')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_reply_to_ticket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instructions for replying to a ticket."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("👉 To reply, please **reply** to the ticket message above with your text.", parse_mode='Markdown')

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a message with an inline keyboard menu."""
    keyboard = [
        [
            InlineKeyboardButton("🧍 Register", callback_data='register'),
            InlineKeyboardButton("� Profile", callback_data='profile'),
        ],
        [
            InlineKeyboardButton("🛒 Make Order", callback_data='order'),
            InlineKeyboardButton("✍️ Feedback", callback_data='feedback'), 
        ],
        [
            InlineKeyboardButton("� Contact Support", callback_data='contact_support'),
        ],
        [
            InlineKeyboardButton("ℹ️ About", callback_data='about'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text('Welcome to ET Honey Trading! Please choose an option:', reply_markup=reply_markup)
    elif update.callback_query:
         # When returning from a conversation or other flow
        await update.callback_query.message.reply_text('Welcome to ET Honey Trading! Please choose an option:', reply_markup=reply_markup)

async def check_registration_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    customer = database.get_customer_by_telegram_id(user_id)

    if not customer:
        message = "You need to register first to use this feature. Please use the /register command."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return False
    
    if customer['status'] == 'Pending':
        message = "Your registration is pending admin approval. Please wait to use this feature."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return False

    if customer['status'] == 'Rejected':
        message = "Your registration was rejected. Please contact support or re-register."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return False

    if customer['status'] == 'Deleted':
        message = "Your account is deleted. Please reactivate or register a new account."
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
        message = "To register, you must have a Telegram username. Please set one in your Telegram settings and try again."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
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

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text("Let's get you registered! First, please enter your *Full Name*:", parse_mode='Markdown')
    else: # triggered via command
        await update.message.reply_text("Let's get you registered! First, please enter your *Full Name*:", parse_mode='Markdown')
        
    return FULL_NAME

async def receive_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores full name and asks for phone number."""
    user_input = update.message.text
    # Validation placeholder
    if len(user_input) < 3:
        await update.message.reply_text("Name is too short. Please enter your full name:")
        return FULL_NAME
    
    context.user_data['full_name'] = user_input
    await update.message.reply_text("Great! Now, please enter your *Phone Number*:", parse_mode='Markdown')
    return PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores phone and asks for email."""
    user_input = update.message.text
    # Validation placeholder (e.g., regex check)
    if not user_input.isdigit(): # Simple check
         await update.message.reply_text("Please enter a valid phone number (digits only):")
         return PHONE

    context.user_data['phone'] = user_input
    await update.message.reply_text("Thanks! Please enter your *Email Address*:", parse_mode='Markdown')
    return EMAIL

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores email and asks for region."""
    user_input = update.message.text
    # Validation placeholder
    if "@" not in user_input:
        await update.message.reply_text("Please enter a valid email address:")
        return EMAIL

    context.user_data['email'] = user_input
    await update.message.reply_text("Please enter your *Region/City*:", parse_mode='Markdown')
    return REGION

async def receive_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores region and asks for customer type."""
    user_input = update.message.text
    context.user_data['region'] = user_input
    
    keyboard = [
        [InlineKeyboardButton("New Customer", callback_data='New'),
         InlineKeyboardButton("Returning Customer", callback_data='Returning')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Are you a *New* or *Returning* customer?", reply_markup=reply_markup, parse_mode='Markdown')
    return CUSTOMER_TYPE

async def receive_customer_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores customer type and asks for confirmation."""
    query = update.callback_query
    await query.answer()
    context.user_data['customer_type'] = query.data
    
    # Summary
    summary = (
        f"*Confirm Registration Details:*\n\n"
        f"👤 Name: {context.user_data['full_name']}\n"
        f"📞 Phone: {context.user_data['phone']}\n"
        f"📧 Email: {context.user_data['email']}\n"
        f"📍 Region: {context.user_data['region']}\n"
        f"🏷 Type: {context.user_data['customer_type']}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data='confirm'),
         InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
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
    
    await query.message.reply_text("✅ Registration submitted successfully! Pending admin approval.")
    
    # Notify Admin
    admin_id = os.getenv("ADMIN_ID")
    if admin_id and admin_id != "your_admin_id_here":
        try:
            keyboard = [
                [InlineKeyboardButton("Approve", callback_data=f"admin:approve:customers:{customer_id}"),
                 InlineKeyboardButton("Reject", callback_data=f"admin:reject:customers:{customer_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = (
                f"🚨 *New Customer Registration*\n\n"
                f"ID: {customer_id}\n"
                f"Telegram ID: {data['telegram_id']}\n"
                f"Username: @{data['username']}\n"
                f"Name: {data['full_name']}\n"
                f"Phone: {data['phone']}\n"
                f"Email: {data['email']}\n"
                f"Region: {data['region']}\n"
                f"Type: {data['customer_type']}"
            )
            await context.bot.send_message(chat_id=admin_id, text=message, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Failed to send admin notification: {e}")
            
    return ConversationHandler.END

async def handle_returning_user_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the choice of a returning user with a deleted account."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == 'reactivate_account':
        database.update_customer_status_by_telegram_id(user_id, 'Pending') # Reactivate as Pending
        await query.message.reply_text("Your old account has been reactivated and is now 'Pending' admin approval. You will be notified once it's approved.")

        # Notify Admin about account reactivation
        admin_id = os.getenv("ADMIN_ID")
        if admin_id and admin_id != "your_admin_id_here":
            try:
                customer = database.get_customer_by_telegram_id(user_id)
                if customer:
                    keyboard = [
                        [InlineKeyboardButton("Approve", callback_data=f"admin:approve:customers:{customer['id']}"),
                         InlineKeyboardButton("Reject", callback_data=f"admin:reject:customers:{customer['id']}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    message = (
                        f"🚨 *Account Reactivation Request*\n\n"
                        f"User: {customer['full_name']} (ID: {user_id})\n"
                        f"Username: @{customer['username']}\n"
                        f"Status: Pending Reactivation\n"
                    )
                    await context.bot.send_message(chat_id=admin_id, text=message, reply_markup=reply_markup, parse_mode='Markdown')
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
    user_id = update.effective_user.id
    customer = database.get_customer_by_telegram_id(user_id)

    if not customer:
        await update.message.reply_text("You don't have an account to delete.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("Yes, delete my account", callback_data='confirm_delete'),
         InlineKeyboardButton("No, keep my account", callback_data='cancel_delete')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Are you sure you want to delete your account? This action is irreversible and will remove all your associated data (orders, tickets, feedback).", reply_markup=reply_markup)
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
    """Cancels and ends the conversation."""
    if update.message:
        await update.message.reply_text('Process cancelled.', reply_markup=ReplyKeyboardRemove())
    elif update.callback_query:
        await update.callback_query.message.reply_text('Process cancelled.')
    return ConversationHandler.END

async def is_admin(username):
    logging.info(f"Checking admin status for username: {username}")
    if not username:
        logging.info(f"Username is empty for admin check.")
        return False
    customer = database.get_customer_by_username(username)
    is_admin_status = customer and customer['is_admin'] == 1
    logging.info(f"Admin status for {username}: {is_admin_status} (Customer data: {customer})")
    return is_admin_status

async def admin_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles admin approval/rejection actions."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(':')
    if len(data) != 4 or data[0] != 'admin':
        return

    action = data[1] # approve or reject
    # entity = data[2] # customers
    entity_id = int(data[3])
    
    if action == 'approve':
        if 'customers' in query.data:
            database.update_customer_status(entity_id, 'Approved')
            new_text = query.message.text + "\n\n✅ *APPROVED*"
            await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=None)
            
            # Notify user
            customer = database.get_customer(entity_id)
            if customer and customer['telegram_id']:
                 try:
                    await context.bot.send_message(chat_id=customer['telegram_id'], text="🎉 Your registration has been approved!")
                 except Exception as e:
                    logging.error(f"Could not notify user: {e}")
        
        elif 'orders' in query.data:
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

        elif 'feedback' in query.data:
            database.update_feedback_status(entity_id, 'Approved')
            new_text = query.message.text + "\n\n✅ *FEEDBACK APPROVED*"
            await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=None)

    elif action == 'reject':
        if 'customers' in query.data:
            database.update_customer_status(entity_id, 'Rejected')
            new_text = query.message.text + "\n\n❌ *REJECTED*"
            await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=None)

            # Notify user and permanently delete their account
            customer = database.get_customer(entity_id)
            if customer and customer['telegram_id']:
                try:
                    database.permanently_delete_customer(customer['telegram_id'])
                    await context.bot.send_message(chat_id=customer['telegram_id'], text="❌ Your account reactivation request has been rejected. Your old account has been permanently deleted, and you can now register as a new user.")
                except Exception as e:
                    logging.error(f"Could not notify user or permanently delete account after rejection: {e}")
            
        elif 'orders' in query.data:
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

        elif 'feedback' in query.data:
            database.update_feedback_status(entity_id, 'Rejected')
            new_text = query.message.text + "\n\n❌ *FEEDBACK REJECTED*"
            await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=None)

        elif 'tickets' in query.data:
            database.update_ticket_status(entity_id, 'Rejected')
            new_text = query.message.text + "\n\n❌ *TICKET REJECTED*"
            await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=None)
            
            # Notify user
            ticket = database.get_ticket(entity_id)
            if ticket and ticket['user_id']:
                 try:
                    await context.bot.send_message(chat_id=ticket['user_id'], text=f"❌ Your Ticket #{entity_id} has been rejected. Please verify your details.")
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
    
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')
        
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
    
    keyboard = [[InlineKeyboardButton("Skip Attachment", callback_data='skip_attachment')]]
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
    
    # Notify Admin
    admin_id = os.getenv("ADMIN_ID")
    if admin_id and admin_id != "your_admin_id_here":
        try:
            keyboard = [
                [InlineKeyboardButton("Approve", callback_data=f"admin:approve:tickets:{ticket_id}"),
                 InlineKeyboardButton("Reject", callback_data=f"admin:reject:tickets:{ticket_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            admin_msg = (
                f"🛠 *New Support Ticket*\n\n"
                f"Ticket: #{ticket_id}\n"
                f"Type: {category}\n"
                f"Subject: {subject}\n"
                f"User: {update.effective_user.full_name} (@{update.effective_user.username or 'NoUsername'}) (ID: {user_id})\n\n"
                f"{message_text}"
            )
            await context.bot.send_message(chat_id=admin_id, text=admin_msg, reply_markup=reply_markup, parse_mode='Markdown')
            
            if attachment_path:
                 # Check if photo or document
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
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.username):
        await query.message.reply_text("You are not authorized.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Product", callback_data='admin_add_product')],
        [InlineKeyboardButton("📋 List Products", callback_data='admin_list_products')],
        [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data='admin')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🛒 *Product Management*\n\nSelect an option:", reply_markup=reply_markup, parse_mode='Markdown')

async def admin_user_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user management menu."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.username):
        await query.message.reply_text("You are not authorized.")
        return

    users = database.get_recent_users(10)
    
    text = "*👥 User Management (Recent 10)*\nSelect a user to manage:\n\n"
    keyboard = []
    
    for u in users:
        status_icon = "✅" if u['status'] == 'Approved' else "⏳" if u['status'] == 'Pending' else "❌"
        display_name = u['username'] if u['username'] else u['full_name']
        keyboard.append([InlineKeyboardButton(f"{status_icon} {display_name} ({u['status']})", callback_data=f"admin_manage_user:{u['id']}")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data='admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

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
    
    if action == 'reject':
        database.update_customer_status(user_id, 'Rejected')
        await query.message.reply_text("User has been banned/rejected.")
    elif action == 'approve':
        database.update_customer_status(user_id, 'Approved')
        await query.message.reply_text("User has been activated/approved.")
    elif action == 'toggle_admin':
        user = database.get_customer(user_id)
        new_status = 0 if user['is_admin'] else 1
        database.set_admin_status(user['telegram_id'], new_status)
        status_str = "Admin" if new_status else "User"
        await query.message.reply_text(f"User is now a {status_str}.")
        
    # Refresh the view
    await admin_manage_user(update, context) # Re-render the user details with updated info

async def admin_reports_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays reports and logs."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.username):
        await query.message.reply_text("You are not authorized.")
        return

    total_revenue = database.get_total_revenue()
    total_orders = database.get_total_orders_count()
    total_tickets = database.get_total_tickets_count()
    total_users = database.get_total_users()
    
    text = (
        "*📈 Reports & Logs*\n\n"
        f"💰 *Total Revenue:* ${total_revenue:,.2f}\n"
        f"🛒 *Total Orders:* {total_orders}\n"
        f"✉️ *Total Tickets:* {total_tickets}\n"
        f"👥 *Total Users:* {total_users}\n"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data='admin')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the add product conversation."""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text("➕ *Add New Product*\n\nPlease enter the *Product Name*:", parse_mode='Markdown')
    return ADD_PRODUCT_NAME

async def receive_add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product_name'] = update.message.text
    await update.message.reply_text("Please enter the *Product Description*:", parse_mode='Markdown')
    return ADD_PRODUCT_DESC

async def receive_add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product_desc'] = update.message.text
    await update.message.reply_text("Please enter the *Price* (e.g., 1500.50):", parse_mode='Markdown')
    return ADD_PRODUCT_PRICE

async def receive_add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['new_product_price'] = price
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a number:")
        return ADD_PRODUCT_PRICE
        
    await update.message.reply_text("Please enter the *Stock Quantity*:", parse_mode='Markdown')
    return ADD_PRODUCT_STOCK

async def receive_add_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("Invalid stock. Please enter a whole number:")
        return ADD_PRODUCT_STOCK
        
    context.user_data['new_product_stock'] = int(update.message.text)
    
    keyboard = [[InlineKeyboardButton("Skip Image", callback_data='skip_image')]]
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
    
    database.add_product(name, desc, price, stock, image)
    
    message = "✅ *Product Added Successfully!*\n\n"
    if update.callback_query:
        await update.callback_query.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, parse_mode='Markdown')

async def admin_list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    products = database.get_all_products()
    if not products:
        await query.message.reply_text("No products found.")
        return

    text = "*📋 Product List*\n\n"
    keyboard = []
    
    for p in products:
        text += f"🔹 *{p['name']}* - ${p['price']} (Stock: {p['stock']})\n"
        keyboard.append([InlineKeyboardButton(f"❌ Delete {p['name']}", callback_data=f"admin_delete_product:{p['id']}")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_products')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_delete_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split(':')[1])
    database.delete_product(product_id)
    
    await query.message.reply_text("🗑 Product deleted.")
    await admin_list_products(update, context)

async def user_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user messages outside of specific flows (checking for open tickets)."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Check for open ticket
    ticket = database.get_active_ticket(user_id)
    
    if ticket:
        ticket_id = ticket['id']
        database.add_message(ticket_id, 'user', message_text)
        
        # Notify Admin
        admin_id = os.getenv("ADMIN_ID")
        if admin_id and admin_id != "your_admin_id_here":
            try:
                admin_message = (
                    f"📩 *New Support Message*\n"
                    f"Ticket: #{ticket_id}\n"
                    f"User: {update.effective_user.full_name} (ID: {user_id})\n\n"
                    f"{message_text}\n\n"
                    f"👉 *Reply to this message to answer.*"
                )
                await context.bot.send_message(chat_id=admin_id, text=admin_message, parse_mode='Markdown')
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
    
    await query.message.reply_text(f"You rated us {rating} stars! ⭐\n\nPlease write a brief comment or review:", parse_mode='Markdown')
    return COMMENT

async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores comment and asks for photo."""
    user_input = update.message.text
    if len(user_input) < 3:
        await update.message.reply_text("Comment is too short. Please write a bit more:")
        return COMMENT
        
    context.user_data['feedback_comment'] = user_input
    
    keyboard = [[InlineKeyboardButton("Skip Photo", callback_data='skip_photo')]]
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
    
    # Notify Admin
    admin_id = os.getenv("ADMIN_ID")
    if admin_id and admin_id != "your_admin_id_here":
        try:
            keyboard = [
                [InlineKeyboardButton("Approve", callback_data=f"admin:approve:feedback:{feedback_id}"),
                 InlineKeyboardButton("Reject", callback_data=f"admin:reject:feedback:{feedback_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = (
                f"✍️ *New Feedback Received*\n\n"
                f"ID: #{feedback_id}\n"
                f"User ID: {user_id}\n"
                f"⭐ Rating: {rating}/5\n"
                f"📝 Comment: {comment}\n"
                f"🖼 Photo: {'Yes' if photo_path else 'No'}"
            )
            await context.bot.send_message(chat_id=admin_id, text=message, reply_markup=reply_markup, parse_mode='Markdown')
            
            if photo_path:
                await context.bot.send_photo(chat_id=admin_id, photo=open(photo_path, 'rb'), caption=f"Photo for Feedback #{feedback_id}")
                
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
        [InlineKeyboardButton("✍️ My Feedback", callback_data='my_feedback')]
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
        text = "🛒 *New Order*\n\nPlease enter the *Product Name* you would like to order:"
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
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
                await query.message.reply_text(f"You selected: *{product['name']}*.\n\nHow many would you like to order? (Please enter a number):", parse_mode='Markdown')
                return QUANTITY
            else:
                 await query.message.reply_text("Product not found. Please select again.")
                 return PRODUCT_NAME
    
    user_input = update.message.text
    if len(user_input) < 2:
        await update.message.reply_text("Product name is too short. Please enter the product name:")
        return PRODUCT_NAME
        
    context.user_data['order_product'] = user_input
    await update.message.reply_text("How many would you like to order? (Please enter a number):")
    return QUANTITY

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores quantity and asks for delivery address."""
    user_input = update.message.text
    if not user_input.isdigit() or int(user_input) <= 0:
        await update.message.reply_text("Please enter a valid quantity (positive number):")
        return QUANTITY
        
    context.user_data['order_quantity'] = int(user_input)
    await update.message.reply_text("Please enter your *Delivery Address*:", parse_mode='Markdown')
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
         InlineKeyboardButton("Bank Transfer", callback_data='Transfer')]
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
    if admin_id and admin_id != "your_admin_id_here":
        try:
            keyboard = [
                [InlineKeyboardButton("Approve", callback_data=f"admin:approve:orders:{order_id}"),
                 InlineKeyboardButton("Reject", callback_data=f"admin:reject:orders:{order_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = (
                f"🛒 *New Order Received*\n\n"
                f"Order ID: #{order_id}\n"
                f"User ID: {user_id}\n"
                f"Product: {product}\n"
                f"Quantity: {quantity}\n"
                f"Address: {address}\n"
                f"Payment: {payment}"
            )
            await context.bot.send_message(chat_id=admin_id, text=message, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Failed to send admin notification for order: {e}")
            
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
    database.set_admin_status(target_telegram_id, 0)
    await update.message.reply_text(f"User {target_telegram_id} has been set as regular user.")

async def order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /order command."""
    await update.message.reply_text("You selected: Make Order (Placeholder)")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /about command."""
    await update.message.reply_text("You selected: About (Placeholder)")

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
    elif choice == 'about':
        await about_command(update, context)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback for unknown messages."""
    await update.message.reply_text("Sorry, I didn't understand that command or message. Type /start to see the menu.")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token or token == "your_bot_token_here":
        print("Error: BOT_TOKEN is not set in .env file.")
        return

    application = ApplicationBuilder().token(token).post_init(post_init).build()

    # Registration Conversation Handler
    registration_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_registration, pattern='^register$'),
            CommandHandler('register', start_registration)
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
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False 
    )

    # Support Conversation Handler
    support_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_support, pattern='^(Inquiry|Complaint|contact_support)$'),
            CommandHandler('support', start_support),
            CommandHandler('complaint', start_support),
            CommandHandler('inquiry', start_support)
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
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    # Feedback Conversation Handler
    feedback_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_feedback, pattern='^feedback$'),
            # No command for feedback initially requested, but can add one if needed
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
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    # Order Conversation Handler
    order_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_order, pattern='^order$'),
            CommandHandler('order', start_order)
        ],
        states={
            PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_product),
                CallbackQueryHandler(receive_product, pattern='^prod:\\d+$')
            ],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)],
            DELIVERY_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address)],
            PAYMENT_TYPE: [CallbackQueryHandler(receive_payment, pattern='^(Cash|Transfer)$')],
            CONFIRM_ORDER: [CallbackQueryHandler(confirm_order_submission, pattern='^(confirm_order|cancel)$')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    # Add Product Conversation Handler
    add_product_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_product, pattern='^admin_add_product$')],
        states={
            ADD_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_name)],
            ADD_PRODUCT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_desc)],
            ADD_PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_price)],
            ADD_PRODUCT_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_product_stock)],
            ADD_PRODUCT_IMAGE: [
                MessageHandler(filters.PHOTO, receive_add_product_image),
                CallbackQueryHandler(skip_add_product_image, pattern='^skip_image$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    # Add Handlers
    application.add_handler(registration_handler)
    application.add_handler(order_handler)
    application.add_handler(support_handler)
    application.add_handler(feedback_handler)
    application.add_handler(add_product_handler)
    
    application.add_handler(CallbackQueryHandler(admin_view_ticket, pattern='^admin_view_ticket:\\d+$'))
    application.add_handler(CallbackQueryHandler(admin_products_menu, pattern='^admin_products$'))
    application.add_handler(CallbackQueryHandler(admin_list_products, pattern='^admin_list_products$'))
    application.add_handler(CallbackQueryHandler(admin_delete_product_handler, pattern='^admin_delete_product:\\d+$'))
    application.add_handler(CallbackQueryHandler(admin_user_messages, pattern='^admin_user_messages(:.+)?$'))
    application.add_handler(CallbackQueryHandler(admin_dashboard_overview, pattern='^admin_dashboard_overview$'))
    application.add_handler(CallbackQueryHandler(admin_user_management_menu, pattern='^admin_user_management$'))
    application.add_handler(CallbackQueryHandler(admin_reports_logs, pattern='^admin_reports_logs$'))
    application.add_handler(CallbackQueryHandler(admin_menu, pattern='^admin$'))
    
    # Newly added admin handlers
    application.add_handler(CallbackQueryHandler(admin_manage_user, pattern='^admin_manage_user:\\d+$'))
    application.add_handler(CallbackQueryHandler(admin_user_action_handler, pattern='^admin_act_user:.+$'))
    application.add_handler(CallbackQueryHandler(admin_reply_to_ticket_callback, pattern='^admin_reply_to_ticket:\\d+$'))
    application.add_handler(CallbackQueryHandler(admin_resolve_ticket_callback, pattern='^admin_resolve_ticket:\\d+$'))
    
    # User Profile Handlers
    application.add_handler(CommandHandler('profile', profile_command))
    application.add_handler(CallbackQueryHandler(profile_command, pattern='^profile$'))
    application.add_handler(CallbackQueryHandler(my_orders_callback, pattern='^my_orders$'))
    application.add_handler(CallbackQueryHandler(my_tickets_callback, pattern='^my_tickets$'))
    application.add_handler(CallbackQueryHandler(view_ticket_callback, pattern='^view_ticket:\\d+$'))
    application.add_handler(CallbackQueryHandler(my_feedback_callback, pattern='^my_feedback$'))

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('admin', admin_menu))
    application.add_handler(CommandHandler("feedback", start_feedback))
    application.add_handler(CommandHandler("setadmin", setadmin))

    application.add_handler(CommandHandler("setuser", set_user))
    application.add_handler(CommandHandler('about', about_command))

    application.add_handler(CallbackQueryHandler(admin_action_handler, pattern='^admin:'))
    # Add the delete account conversation handler
    delete_account_handler = ConversationHandler(
        entry_points=[CommandHandler('deleteaccount', start_delete_account)],
        states={
            CONFIRM_DELETE: [CallbackQueryHandler(confirm_delete_account, pattern='^(confirm_delete|cancel_delete)$')]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    application.add_handler(delete_account_handler)

    application.add_handler(CallbackQueryHandler(button_handler)) # For other menu buttons

    # Admin Reply Handler (Must be before general fallback)
    # Using filters.REPLY to catch replies
    application.add_handler(MessageHandler(filters.REPLY, admin_reply_handler))
    
    # General User Message Handler (for continuing open tickets or fallback)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_reply_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
