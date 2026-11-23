# DBMS Project - Backend

Modular Flask backend providing schema design sync, query generation and execution, DML operations, and database normalization analysis.

## Structure

```
backend/
├── config.py                 # Configuration and environment variables
├── database.py               # MySQL database connection helper
├── utils/                    # Shared helper utilities
│   ├── sanitizer.py          # SQL identifier sanitization
│   └── query_builder.py      # WHERE clause dynamic SQL builder
├── services/                 # Core business and database logic
│   ├── schema_service.py     # Schema synchronization, table inspection
│   ├── query_service.py      # Dynamic SELECT builder & executor
│   ├── dml_service.py        # INSERT / UPDATE / DELETE operations
│   └── normalization_service.py # Closure calculation, Candidate Keys, 1NF/2NF/3NF/BCNF
├── routes/                   # API Blueprint route definitions
│   ├── general_routes.py     # /api/ping, /api/db_test
│   ├── schema_routes.py      # /api/schema, /api/tables, /api/table_details, /api/current_schema
│   ├── query_routes.py       # /api/execute_select
│   ├── dml_routes.py         # /api/execute_dml
│   └── normalization_routes.py # /api/analyze_normalization
├── app.py                    # Main Flask entry point (application factory)
├── requirements.txt          # Python dependencies
└── .env.example              # Sample environment variable settings
```

## Running the Backend

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Create a `.env` file from `.env.example` and set your MySQL credentials:
   ```bash
   cp .env.example .env
   ```

3. Start the server:
   ```bash
   python app.py
   ```
