# Deployment Guide for ET Honey Trading Bot

This guide explains how to deploy your bot to a live server so it runs 24/7.

## Option 1: PythonAnywhere (Recommended for SQLite)
PythonAnywhere is great for bots using SQLite because it has a persistent filesystem (your database won't be deleted when the server restarts).

1.  **Sign Up**: Go to [www.pythonanywhere.com](https://www.pythonanywhere.com/) and create a free beginner account.
2.  **Upload Code**:
    *   Go to the "Files" tab.
    *   Upload your project files (`bot.py`, `database.py`, `languages.py`, `requirements.txt`, `.env`).
    *   *Note*: Ensure they are in the correct folder structure (e.g., inside a folder named `ET_HONEY`).
3.  **Install Dependencies**:
    *   Go to the "Consoles" tab and open a **Bash** console.
    *   Run: `pip3 install -r requirements.txt --user`
4.  **Run the Bot**:
    *   In the Bash console, run: `python3 ET_HONEY/bot.py`
    *   **Important**: The free tier closes consoles after some time. For a permanent 24/7 bot on the free tier, you might need to manually restart it occasionally or upgrade to the $5/month "Hacker" plan which supports "Always-on tasks".

## Option 2: Render.com (Free Tier)
Render is a modern cloud platform.

**Warning**: The free tier of Render (and similar services) usually has an "ephemeral" filesystem. This means **your SQLite database will be reset** every time you deploy or the server restarts. To use Render effectively, you should ideally switch to an external database (like PostgreSQL) or use a "Disk" (which costs money).

If you just want to test it live (and don't mind data resetting):
1.  **Push to GitHub**: Upload your code to a GitHub repository.
2.  **Create Web Service**:
    *   Sign up at [render.com](https://render.com).
    *   Click "New +" -> "Web Service".
    *   Connect your GitHub repo.
3.  **Configuration**:
    *   **Runtime**: Python 3
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `python ET_HONEY/bot.py`
    *   **Environment Variables**: Add `BOT_TOKEN` and `ADMIN_ID` here.

## Prerequisite Files (Created for you)
We have already created the necessary configuration files for you:
*   `requirements.txt`: Lists all the libraries your bot needs.
*   `Procfile`: Used by services like Heroku/Railway.

## Security Note for Live Server
*   **Never share your `.env` file** publicly or commit it to a public GitHub repository.
*   On cloud services, use their "Environment Variables" settings page to input your `BOT_TOKEN`.
