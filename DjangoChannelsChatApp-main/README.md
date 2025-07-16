
---

# Django Channels Real-Time Chat App

A modern, real-time chat application built with Django, Django Channels, and WebSockets. The UI features a split-pane design: chat list on the left and active chat on the right, all in a single-page, real-time experience.

---

## Features

* **Split layout UI:** Chat list (users/groups) on the left, active chat on the right
* **Real-time messaging:** Powered by Django Channels and WebSockets
* **Persistent chat history:** Previous messages load instantly when you open a chat
* **Online status & last seen:** See who's online and their last active time (green dot with tooltip)
* **Group and private chats:** Create, join, and chat in groups or one-on-one
* **Responsive design:** Works on desktop and mobile
* **No page reloads:** All chat actions are AJAX/WebSocket-driven
* **Login is the default landing page:** Users must log in to access the dashboard

---

## Project Structure

```
DjangoChannelsChatApp-main/
│
├── accounts/                # User accounts, profiles, online status
│
├── ChatApp/                 # Main chat logic (models, views, consumers, routing)
│   └── templates/
│       └── dashboard.html   # Main chat dashboard (split UI)
│
├── ChatProject/             # Django project settings and URLs
│
├── templates/               # All main templates (login, register, base, 404, etc.)
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── 404.html
│   └── ...
│
├── static/                  # Static files (CSS, images)
│
├── db.sqlite3               # SQLite database (for development)
│
├── manage.py
├── README.md
└── SPECIFICATION.md
```

---

## Application Flow

1. **Landing Page:**

   * `/` redirects to the login page (`login.html`).
   * Only authenticated users can access the dashboard.

2. **Dashboard (`/dashboard/`):**

   * Split-pane layout:

     * **Left:** Chat list (users/groups), new chat/group buttons, online status indicators.
     * **Right:** Active chat window, real-time messages, avatars, message input.
   * All chat actions (switching chats, sending messages, creating groups) are handled dynamically via AJAX/WebSockets—no page reloads.

3. **Real-Time Features:**

   * New messages appear instantly for all participants.
   * Online status and last seen are updated live.
   * Chat list and chat window stay in sync.

4. **Streamlined Interface:**

   * All outdated chat, message, and room templates have been removed.
   * The only interface for chat is the dynamic dashboard.

---

## Setup

1. **Clone the repository**
2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
3. **Apply migrations**

   ```bash
   python manage.py migrate
   ```
4. **Create a superuser (optional, for admin access)**

   ```bash
   python manage.py createsuperuser
   ```
5. **Run the development server**

   ```bash
   python manage.py runserver
   ```
6. **Access the app**

   * Go to [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   * You will be redirected to the login page
   * Register/login and start chatting!

---

## License

MIT

---
