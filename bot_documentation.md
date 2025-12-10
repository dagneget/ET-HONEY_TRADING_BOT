# Bot Documentation

This document outlines the current functionalities of the Telegram bot and potential future enhancements.

## Current Features

The bot currently supports the following features, primarily managed through `bot.py` and interacting with `database.py` for data persistence:

### 1. User Registration
- **Commands/Entry Points**: `/start`, `/register`, CallbackQueryHandler for `register` pattern.
- **Flow**: Guides new users through a conversation to collect `FULL_NAME`, `PHONE`, `EMAIL`, `REGION`, and `CUSTOMER_TYPE`.
- **Admin Approval**: New registrations are `Pending` and require admin approval. Admins are notified of new registrations.
- **Returning Users**: Handles users with previously deleted accounts, offering options to `reactivate_account` (as Pending) or `register_new_account` (permanently deleting the old one).
- **Username Requirement**: Users must have a Telegram username to register.

### 2. Order Management
- **Commands/Entry Points**: `/order`, CallbackQueryHandler for `order` pattern.
- **Flow**: Collects `PRODUCT_NAME`, `QUANTITY`, `DELIVERY_ADDRESS`, and `PAYMENT_TYPE`.
- **Admin Notification**: Admins are notified of new orders and can approve/reject them.

### 3. Product Display with Images
- **Feature**: When products are displayed to users, they now include images that were inserted by the admin, enhancing the user's browsing experience.

### 4. Feedback Submission
- **Commands/Entry Points**: `/feedback`, CallbackQueryHandler for `feedback` pattern.
- **Flow**: Allows users to submit `RATING`, `COMMENT`, and optionally a `PHOTO`.
- **Admin Approval**: Feedback can be approved by admins.

### 4. Support/Ticket System (Complaint/Inquiry)
- **Commands/Entry Points**: `/complaint`, `/inquiry`, CallbackQueryHandler for `Inquiry` or `Complaint` patterns.
- **Simplified Flow**: Users can directly submit their complaint or inquiry message without needing to provide a subject. The bot automatically categorizes the request.
- **Admin Interaction**: Admins can view tickets, including the user's profile information for identification, and reply to users. Users can also reply to admin messages, continuing the conversation.
- **Ticket History**: Users can view their past tickets and the conversation history with admins.

### 5. Account Management
- **Account Deletion**: 
  - **Commands/Entry Points**: `/deleteaccount`.
  - **Flow**: Prompts user for confirmation before `permanently_delete_customer`.
  - **Irreversible Action**: Emphasizes that deletion is irreversible and removes all associated data.

### 6. User Profiles
- **Commands/Entry Points**: `/profile`, CallbackQueryHandler for `profile` pattern.
- **Feature**: Users can view their registered information, order history (`My Orders`), and ticket history (`My Tickets`) including conversation details.

### 7. Admin Functionality
- **Commands/Entry Points**: `/admin`, `/setadmin`, `/setuser`, CallbackQueryHandlers for `admin` patterns.
- **Admin Dashboard**: Provides an `admin_menu` with options like `admin_dashboard_overview`, `admin_view_ticket`, `admin_user_messages`.
- **User Management**: Admins can `set_admin_by_username` (or `set_admin_status` by Telegram ID) and `set_user` (remove admin status).
- **Approval/Rejection**: Admins can approve/reject customer registrations, orders, and feedback.
- **Admin Reply**: Admins can reply to user tickets, and these replies are routed back to the user.

### 8. General Bot Commands
- `/start`: Opens the main menu.
- `/about`: Provides information about the bot (currently a placeholder).
- `/cancel`: Cancels any ongoing conversation.
- `unknown`: Fallback for unrecognized commands/messages.

## Technical Details
- **Database**: SQLite (`honey_trading.db`) managed by `database.py`.
- **Environment Variables**: Uses `.env` for `BOT_TOKEN` and `ADMIN_ID`.
- **Logging**: Basic logging is enabled for tracking bot operations and errors.
- **Conversation Handlers**: Utilizes `telegram.ext.ConversationHandler` for multi-step interactions (Registration, Order, Feedback, Support, Account Deletion).
- **Inline Keyboards**: Extensively uses `InlineKeyboardButton` and `InlineKeyboardMarkup` for interactive menus and confirmations.
- **File Uploads**: Supports photo and document uploads for tickets and feedback.

## Future Additions / Enhancements

Based on the current structure and common bot requirements, the following features could be considered for future development:

1.  **Product Catalog Management**: 
    - Allow admins to add, edit, and remove products from a catalog.
    - Enable users to browse products with more details (descriptions, prices, images).
    - Integrate with the order system for easier product selection.

2.  **Payment Gateway Integration**: 
    - Implement actual payment processing (e.g., Stripe, PayPal) instead of just `Cash` or `Transfer` options.
    - Provide secure transaction handling and order confirmation.

3.  **Notification System**: 
    - Proactive notifications for order status updates, new product announcements, or important alerts.
    - Customizable notification preferences for users.

4.  **Multi-language Support**: 
    - Implement internationalization (i18n) to support multiple languages.
    - Allow users to select their preferred language.

5.  **Advanced Admin Dashboard**: 
    - More comprehensive analytics and reporting for admin activities.
    - Tools for bulk user management or broadcast messages.
    - Dedicated sections for managing product inventory, promotions, and customer support.

6.  **FAQ/Knowledge Base**: 
    - A searchable FAQ section to answer common user questions.
    - Reduce the load on the support ticket system.

7.  **Enhanced Security**: 
    - Implement more robust authentication mechanisms if needed.
    - Regular security audits and updates.

8.  **Deployment Automation**: 
    - Scripts or configurations for easier deployment to various hosting environments.
    - Continuous Integration/Continuous Deployment (CI/CD) pipeline setup.

This documentation will be updated as the bot evolves and new features are implemented.