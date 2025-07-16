
---

# Django Channels Chat App - Specification Document

## Overview

This project is a real-time chat application built with Django, Django Channels, and Django REST Framework. It features user authentication (register/login), a split-pane chat dashboard, and real-time messaging in a responsive, modern interface.

## Features

* User registration and login with Django authentication (login is the default landing page)
* Split dashboard layout: chat list (users/groups) on the left, active chat on the right
* All chat interactions occur on a single dashboard page (`dashboard.html`)
* Real-time messaging using Django Channels (WebSockets)
* Online status and last seen indicators (green dot with tooltip)
* Group and private chats (create, join, and chat)
* Persistent chat history (loads instantly when a conversation is opened)
* Responsive, modern UI for desktop and mobile
* No page reloads: all chat actions are handled via AJAX/WebSocket
* Custom 404 error page with modern design

## Directory Structure

```
DjangoChannelsChatApp-main/
├── manage.py
├── db.sqlite3
├── requirements.txt
├── static/
│   └── (static files, e.g. images)
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── 404.html
├── ChatProject/
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── ChatApp/
│   ├── models.py
│   ├── views.py
│   ├── consumers.py
│   ├── routing.py
│   └── ...
├── accounts/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── ...
```

## Key Pages & Templates

* **login.html**: User login form (default landing page)
* **register.html**: User registration form
* **dashboard.html**: Split-interface chat layout (main chat experience)
* **404.html**: Custom error page
* **base.html**: Shared layout, includes Google Fonts and base styles

## Static Files

* All static files (images, CSS, JS) are placed in the `static/` directory.

## Error Handling

* Custom 404 page for missing pages
* Templates follow Django best practices with proper blocks and tags
* All forms include CSRF protection

## Integration Notes

* All `{% url %}` tags reference valid named URLs
* `{% load static %}` is included wherever `{% static %}` is used
* All templates extend `base.html` for consistent layout and styling
* Static files are served via Django's `staticfiles` app during development

## Deployment Notes

* Set `DEBUG = False` and configure `STATIC_ROOT` for production
* Use `collectstatic` to prepare static files for deployment
* Configure a web server (e.g., Nginx) to serve static assets in production

## Customization

* To change the background, update the background image in your CSS
* To add new features, follow Django best practices for modular apps, views, and templates

---

