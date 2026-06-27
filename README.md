# Esports Intelligence Platform

A comprehensive **esports analytics and data engineering** portfolio project built with PostgreSQL, FastAPI, Apache Airflow, and dbt.

This project demonstrates end-to-end data engineering skills: schema design, query optimization, ETL orchestration, caching, and production-style data pipelines.

![Project Architecture](https://via.placeholder.com/800x300?text=Project+Architecture)

## ✨ Key Features

- Complete esports data model (Players, Teams, Matches, Stats, ELO, Prizes)
- FastAPI REST API with Redis caching for leaderboards
- Scheduled ETL pipelines using Apache Airflow
- Data transformations using dbt (Staging → Intermediate → Marts)
- Advanced PostgreSQL features (Triggers, Indexes, MVCC, PgBouncer)
- Analytics exports to local files and AWS S3 data lake

## 🛠 Tech Stack

| Layer              | Technologies |
|--------------------|--------------|
| **Backend**        | FastAPI, Python 3.11, SQLAlchemy, Pydantic |
| **Database**       | PostgreSQL 16, TimescaleDB, PgBouncer |
| **Caching**        | Redis 7 |
| **Orchestration**  | Apache Airflow 2.8 |
| **Transformations**| dbt (1.9) |
| **Container**      | Docker + Docker Compose |
| **Cloud**          | AWS S3 (Data Lake) |

## 🚀 Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd my-postgres-project

# Start all services
docker compose up -d

# Install Python dependencies
pip install -r requirements.txt

# Start the API
uvicorn api.main:app --reload --port 8000
Open API docs at: http://localhost:8000/docs
📁 Project Structure
textmy-postgres-project/
├── api/                    # FastAPI application
├── airflow/dags/           # Airflow ETL pipelines
├── esports_dbt/            # dbt data transformations
├── cache/                  # Redis caching layer
├── scripts/                # Maintenance & export scripts
├── queries/                # Analytical SQL queries
├── migrations/             # Alembic database migrations
├── s3/                     # AWS S3 data lake scripts
├── compose.yaml            # Docker services
└── requirements.txt
🗄️ Database Features Showcased

Advanced indexing and query optimization
PL/pgSQL triggers (team stats, audit logging)
MVCC and VACUUM maintenance
Connection pooling with PgBouncer
Realistic test data generation

📊 Analytics & Data Pipelines

9 optimized analytical queries (KDA, win rates, streaks, prize earnings, etc.)
Nightly/Weekly ETL pipelines with Airflow
dbt models following medallion architecture
Automated data exports to S3

📋 API Endpoints
Interactive documentation available at /docs when running locally.
🐳 Docker Services

PostgreSQL + PgBouncer
Redis
Airflow (Web + Scheduler)
pgAdmin
dbt

📚 Additional Documentation

OPTIMIZATION_REPORT.md — Query performance analysis
mvcc_demo.md — MVCC and maintenance walkthrough
