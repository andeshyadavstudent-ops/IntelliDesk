# 🤖 IntelliDesk — AI-Based IT Helpdesk Automation Platform

## 📌 Overview

**IntelliDesk** is a full-stack AI-powered IT helpdesk system that automates user support using Natural Language Processing (NLP).
It allows users to interact with an AI chatbot for common IT issues and automatically generates support tickets when needed.

The system also provides an admin dashboard for managing tickets, monitoring activity, and analyzing support trends.

---

## 🚀 Features

### 👤 User Features

* Secure Login & Registration (JWT-based authentication)
* AI chatbot for IT support queries
* Automatic ticket creation based on user intent
* View and manage personal tickets
* Real-time chat interface

### 🛠️ Admin Features

* Admin dashboard with ticket overview
* Filter tickets by status, category, and priority
* Update ticket status and priority
* View analytics and system activity
* Manage all user tickets

### 🤖 AI Capabilities

* Zero-shot classification using HuggingFace Transformers
* Intent detection (WiFi issues, password reset, hardware problems, etc.)
* Confidence-based decision making
* Automatic escalation to support tickets

---

## 🧰 Tech Stack

| Layer    | Technology               |
| -------- | ------------------------ |
| Backend  | FastAPI (Python)         |
| Frontend | Jinja2 + Bootstrap 5     |
| Database | MySQL (XAMPP)            |
| ORM      | SQLAlchemy               |
| AI/NLP   | HuggingFace Transformers |
| Auth     | JWT + Bcrypt             |
| Server   | Uvicorn                  |

---

## 📂 Project Structure

```
intellidesk/
│
├── main.py
├── config.py
├── models.py
├── auth.py
│
├── routes/
│   ├── auth_routes.py
│   ├── ticket_routes.py
│   ├── chat_routes.py
│   └── admin_routes.py
│
├── services/
│   ├── nlp_service.py
│   └── ticket_service.py
│
├── templates/
├── static/
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation & Setup

### 1️⃣ Prerequisites

* Python 3.10 or higher
* XAMPP (for MySQL database)

---

### 2️⃣ Clone Repository

```
git clone https://github.com/varunbulkr/IT_capstone_intellidesk
cd intellidesk
```

---

### 3️⃣ Create Virtual Environment

```
python -m venv venv
```

---

### 4️⃣ Activate Virtual Environment

**Windows:**

```
venv\Scripts\activate
```

---

### 5️⃣ Install Dependencies

```
pip install -r requirements.txt
```

---

### ⚠️ Important Fix (NumPy Compatibility)

```
pip install numpy==1.26.4
```

---

### 6️⃣ Setup Database

1. Open XAMPP Control Panel
2. Start **Apache** and **MySQL**
3. Open phpMyAdmin:

```
http://localhost/phpmyadmin
```

4. Create a database:

```
intellidesk
```

---

### 7️⃣ Run Application

```
python -m uvicorn main:app --reload --port 8000
```

---

### 8️⃣ Open in Browser

```
http://localhost:8000
```

---

## 🔑 Demo Credentials

| Role  | Email                                                 | Password |
| ----- | ----------------------------------------------------- | -------- |
| Admin | [admin@intellidesk.com](mailto:admin@intellidesk.com) | admin123 |
| User  | [varun@intellidesk.com](mailto:varun@intellidesk.com) | user123  |

---

## 🔁 Restarting the Project

1. Start XAMPP (Apache + MySQL)
2. Activate virtual environment
3. Run:

```
python -m uvicorn main:app --reload --port 8000
```

---

## 🧪 Example Use Cases

* “My WiFi is not working” → AI detects issue → creates ticket
* “Reset my password” → AI provides solution
* Low confidence → escalates to human support

---

## 📊 Future Improvements

* Email notifications for tickets
* Real-time updates (WebSockets)
* AI model fine-tuning
* Cloud deployment (AWS/Azure)
* Role-based access improvements

---

## 🧠 Learning Outcomes

This project demonstrates:

* Full-stack web development
* REST API design with FastAPI
* AI integration using NLP models
* Database design with SQLAlchemy
* Authentication and security practices
* Debugging and dependency management

---

## 👨‍💻 Author

**Varun Kumar, Avi Bhutani, Andesh Yadav**
Bachelor of Information Technology
Victoria University

---

## 📜 License

This project is for educational purposes only.

---

## 🙌 Acknowledgements

* HuggingFace Transformers
* FastAPI Documentation
* Bootstrap Framework

---
