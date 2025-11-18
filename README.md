# **Online Poll System Backend**

## **1. Introduction**

The Online Poll System Backend is a RESTful API built using Django and Django REST Framework.
It allows users to create polls, add options, cast votes, and retrieve real-time voting results.
The backend simulates real-world poll systems that require efficient data handling, real-time computation, and clear API documentation.

This project is part of the ALX Backend ProDev program and demonstrates key backend engineering skills including API design, relational database modeling, and validation logic.

---

## **2. Real-World Application**

Online polling systems are used in:

* Event/live show voting
* Product feedback and surveys
* Audience interaction tools
* Social media polls
* Classroom assessments

This backend supports real-world demands such as:

* High-frequency voting
* Real-time result updates
* Duplicate-vote prevention
* Poll expiration handling

---

## **3. Project Objectives**

### **API Development**

* Endpoints for creating polls and options
* Voting endpoint with validation
* Results endpoint for real-time vote counts

### **Database Efficiency**

* Normalized schema (Poll, Option, Vote)
* Vote uniqueness enforced with constraints
* Optimized aggregation queries

### **Documentation**

* API documentation generated using **drf-yasg**
* Swagger UI accessible at `/api/docs`
* Project README detailing setup and usage

---

## **4. Technologies Used**

* **Django** – Backend framework
* **Django REST Framework** – REST API toolkit
* **PostgreSQL** – Primary database
* **drf-yasg** – Swagger/OpenAPI documentation generator
* **Python 3.10+** – Programming language

---

## **5. Key Features**

### **Poll Management**

* Create polls with multiple options
* Add descriptions and expiry dates
* Retrieve poll details and options

### **Voting System**

* Cast a vote for a specific option
* Duplicate-vote prevention per poll
* Ensure voting only happens before poll expiry
* Support for anonymous or authenticated voting

### **Real-Time Results**

* Count votes per option
* Calculate total votes for a poll
* Return up-to-date results on request

### **API Documentation**

* Auto-generated Swagger UI using drf-yasg
* Available at:
  `http://localhost:8000/api/docs/`
* Includes schemas, examples, and validation rules

---

## **6. System Requirements**

### **Software Requirements**

* Python 3.10+
* PostgreSQL 12+
* Virtual environment (venv) or pipenv

### **Dependencies**

Installed via `requirements.txt`:

* Django
* Django REST Framework
* drf-yasg
* psycopg2 (PostgreSQL adapter)

---

## **7. Project Setup**

### **Clone Repository**

```bash
git clone <your-repo-url>
cd online-poll-backend
```

### **Create and Activate Virtual Environment**

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

### **Install Dependencies**

```bash
pip install -r requirements.txt
```

### **Environment Variables**

Create a `.env` file:

```
SECRET_KEY=your_secret_key
DATABASE_NAME=polls_db
DATABASE_USER=postgres
DATABASE_PASSWORD=yourpassword
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

### **Run Database Migrations**

```bash
python manage.py migrate
```

### **Start Development Server**

```bash
python manage.py runserver
```

API is now available at:

```
http://127.0.0.1:8000/
```

Swagger docs:

```
http://127.0.0.1:8000/api/docs/
```

---

## **8. API Endpoints Overview**

### **Poll Endpoints**

* `POST /api/polls/` – Create poll
* `GET /api/polls/` – List all polls
* `GET /api/polls/<id>/` – Retrieve a poll

### **Voting Endpoint**

* `POST /api/polls/<id>/vote/` – Cast a vote

### **Results Endpoint**

* `GET /api/polls/<id>/results/` – Get poll results

Full documentation available via Swagger UI.

---

## **9. Running Tests**

```bash
python manage.py test
```
