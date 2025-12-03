# Infrastructure: PostgreSQL

Database schema and migration scripts for Nyx Venatrix.

## Schema

The database is designed to support a complex, multi-agent system with extensive logging and analytics.

### Key Domains

1.  **Identity**: `users`, `user_profiles`, `resumes`
2.  **Sourcing**: `job_posts`, `companies`, `job_sources`
3.  **Execution**: `applications`, `application_sessions`
4.  **Observability**: `application_events`, `model_usage_logs`
5.  **Configuration**: `system_config`

## Migrations

### `001_schema.sql`
The master schema definition. Contains:
- **40+ Tables**: Covering all system domains.
- **pgvector**: Enabled for vector similarity search on job descriptions.
- **Indexes**: Optimized for frequent query patterns.
- **Triggers**: For automatic timestamp updates (`updated_at`).

## Setup

A bootstrap script (`000_create_databases.sh`) runs automatically inside the container to provision both the `nyx_venatrix` and `saturnus` databases on first start. After the container is healthy, apply the schema manually if needed:

```bash
docker exec -i nyx_venatrix_postgres psql -U postgres -d nyx_venatrix < 001_schema.sql
```
