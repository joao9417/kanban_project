# Kanban Project

A simple Kanban board application built with Django and Tailwind CSS.

## Prerequisites

- Python 3.10+
- Git

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd kanban_project
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Apply migrations**:
    ```bash
    python manage.py migrate
    ```

5.  **Run the server**:
    ```bash
    python manage.py runserver
    ```

## features

-   User Registration and Login
-   Create multiple Boards
-   Add Columns and Cards to Boards
-   Kanban view with horizontal scrolling
