# Accessible — MySQL Visual Web Studio

**Accessible** is an interactive, full-stack visual workspace designed to simplify MySQL database management. It enables developers and students to visually design schemas, build complex SQL queries with joins and aggregates, perform live CRUD operations, and verify database normalization (1NF through BCNF) without writing raw SQL queries manually.

---

## 🌟 Key Features

- **Visual Schema Design Canvas**:
  - Interactive drag-and-drop table nodes powered by `@xyflow/react`.
  - Define columns, data types (`INT`, `VARCHAR`, `TEXT`, `DATE`, `BOOLEAN`, `DECIMAL`), and constraints (`Primary Key`, `Not Null`, `Unique`).
  - Visually connect foreign key relationships between tables.
  - Automatically syncs and applies schema changes directly into MySQL.

- **Visual Query Builder (Data Selection)**:
  - Construct dynamic multi-table `SELECT` queries through an intuitive interface.
  - Define `INNER JOIN`, `LEFT JOIN`, and `RIGHT JOIN` conditions visually.
  - Apply filter conditions (`WHERE`) with custom comparison operators and `AND`/`OR` logic.
  - Compute aggregate values (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`) with custom aliases and `GROUP BY` grouping.

- **Interactive CRUD Operations**:
  - **Insert**: Insert single or batch multi-row records with dynamic column inputs.
  - **Update**: Modify existing database records using custom `SET` attributes and targeted `WHERE` criteria.
  - **Delete**: Safely remove records matching specific conditional filters.
  - **Data Viewer**: Inspect live table contents directly inside the interface.

- **Relational Normalization Analyzer**:
  - Computes attribute closures ($X^+$) and calculates minimal candidate keys.
  - Evaluates schema compliance against **1NF**, **2NF** (partial dependencies), **3NF** (transitive dependencies), and **BCNF** (superkey determinants).
  - Outlines exact dependency violations with diagnostic guidance.

- **Refined User Experience**:
  - Responsive landing page dashboard with quick-access feature cards.
  - Sticky navigation header with active route tracking across tools.

---

## 🛠️ Tech Stack

- **Frontend**: React 18, React Router, `@xyflow/react` (React Flow), Axios, Modern CSS
- **Backend**: Python 3.8+, Flask (modular Blueprints), `mysql-connector-python`, `flask-cors`, `python-dotenv`
- **Database**: MySQL Server 8.0+

---

## 📁 Repository Structure

```
DBMS-Project/
├── backend/
│   ├── config.py                 # Configuration and environment variables
│   ├── database.py               # Database connection helper
│   ├── utils/                    # Helper utilities
│   │   ├── sanitizer.py          # SQL identifier sanitization
│   │   └── query_builder.py      # Dynamic WHERE clause builder
│   ├── services/                 # Business logic and database operations
│   │   ├── schema_service.py     # Schema sync and table inspection
│   │   ├── query_service.py      # SELECT query building & execution
│   │   ├── dml_service.py        # INSERT, UPDATE, DELETE execution
│   │   └── normalization_service.py # Closure, candidate keys, normalization
│   ├── routes/                   # API Blueprint route endpoints (/api)
│   │   ├── general_routes.py     # Ping & DB connection test
│   │   ├── schema_routes.py      # Canvas schema and table metadata
│   │   ├── query_routes.py       # Query execution
│   │   ├── dml_routes.py         # CRUD operations
│   │   └── normalization_routes.py # Normalization analysis
│   ├── app.py                    # Flask application factory and entry point
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example              # Sample environment template
│   └── README.md                 # Backend documentation
├── frontend/
│   ├── public/                   # HTML template and static assets
│   ├── src/
│   │   ├── App.js                # Core UI router, pages, and layout
│   │   ├── App.css               # Global application styling and header
│   │   ├── TableNode.js          # Custom React Flow table node component
│   │   └── index.js              # React DOM initialization
│   └── package.json              # Node dependencies and scripts
├── .gitignore                    # Git exclusion rules
└── README.md                     # Main project documentation
```

---

## 🚀 Getting Started

Follow these steps to set up and run the application locally.

### 1. Prerequisites

Ensure the following tools are installed on your system:
- **Python** (version 3.8 or higher)
- **Node.js** (version 18 or higher) & **npm**
- **MySQL Server** (version 8.0 or higher) running locally on port `3306`
- **Git**

---

### 2. Database Setup

1. Start your MySQL service:
   - On Windows: Run `net start MySQL80` or use Windows Services (`services.msc`).
   - On macOS / Linux: `sudo systemctl start mysql` or `brew services start mysql`.

2. Log into MySQL and create the database:
   ```sql
   CREATE DATABASE IF NOT EXISTS mydatabase;
   ```

---

### 3. Backend Setup & Run

Open a terminal window and follow these steps:

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Create a `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```
   *(On Windows Command Prompt: `copy .env.example .env`)*

   Edit `.env` to match your local MySQL configuration:
   ```ini
   MYSQL_HOST=localhost
   MYSQL_USER=root
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_DB=mydatabase

   HOST=0.0.0.0
   PORT=5000
   DEBUG=True
   ```

4. **Start the backend server:**
   ```bash
   python app.py
   ```
   The Flask server will start listening at `http://127.0.0.1:5000`.

---

### 4. Frontend Setup & Run

Open a **second** terminal window:

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node dependencies:**
   ```bash
   npm install
   ```

3. **Start the React development server:**
   ```bash
   npm start
   ```

Your web browser will automatically open **`http://localhost:3000`**.

---

## 🌐 Application Navigation

| Tab | URL | Purpose |
| :--- | :--- | :--- |
| **Home** | `/` | Overview dashboard with direct links to tools |
| **Canvas** | `/canvas` | Interactive schema design canvas and live DB sync |
| **Data Selection** | `/select` | Visual query builder with joins, filters, and aggregates |
| **CRUD** | `/crud` | Record insertion, conditional updates, and deletions |
| **Normalization** | `/normalization` | Functional dependency analyzer (1NF, 2NF, 3NF, BCNF) |

---

## 🔒 Security Note

Sensitive configuration parameters (such as database passwords) must be stored inside `backend/.env`. The `.gitignore` file is configured to ensure `.env` and local temporary build files are never committed to version control.

---

## 📄 License

This project is licensed under the MIT License.
