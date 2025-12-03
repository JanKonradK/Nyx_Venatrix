# Shared Database Infrastructure

This directory contains the shared database infrastructure that can be used across multiple projects.

## Services Included

1. **PostgreSQL 16 with pgvector** - Main database with vector extension
2. **Redis 7** - Cache and queue management
3. **Qdrant** - Vector database for embeddings

## Quick Start

### Start Shared PostgreSQL Only

```bash
docker compose -f ../docker-compose.shared-db.yml up -d
```

This launches the standalone PostgreSQL stack (with the `000_create_databases.sh` init script creating both `nyx_venatrix` and `saturnus` databases) while exposing the `shared_db_network` bridge.

### Start Full Infrastructure (Postgres + Redis + Qdrant)

```bash
cd infrastructure
docker-compose -f docker-compose.infrastructure.yml up -d
```

### Stop Infrastructure

```bash
docker-compose -f docker-compose.infrastructure.yml down
```

### View Logs

```bash
docker-compose -f docker-compose.infrastructure.yml logs -f
```

## Connection Details

### PostgreSQL
- **Host**: localhost
- **Port**: 5432
- **User**: postgres (configurable via POSTGRES_USER)
- **Password**: postgres (configurable via POSTGRES_PASSWORD)
- **Database**: nyx_venatrix (configurable via POSTGRES_DB)
- **Connection URL**: `postgres://postgres:postgres@localhost:5432/nyx_venatrix`

### Redis
- **Host**: localhost
- **Port**: 6379
- **Connection URL**: `redis://localhost:6379`

### Qdrant
- **HTTP Port**: 6333
- **gRPC Port**: 6334
- **Dashboard**: http://localhost:6333/dashboard
- **Connection URL**: `http://localhost:6333`

## Using with Other Projects

Other projects can connect to these services by:

1. Using `shared_db_network` network in their docker-compose.yml:
```yaml
networks:
  shared_db_network:
    external: true
    name: shared_db_network
```

2. Referencing services by container name:
   - `shared_postgres`
   - `shared_redis`
   - `shared_qdrant`

Example connection in another project:
```yaml
services:
  my_app:
    environment:
      - DATABASE_URL=postgres://postgres:postgres@shared_postgres:5432/nyx_venatrix
    networks:
      - shared_db_network
networks:
  shared_db_network:
    external: true
```

## Data Persistence

All data is stored in named volumes:
- `shared_postgres_data` - PostgreSQL data
- `shared_redis_data` - Redis data
- `shared_qdrant_data` - Qdrant vector storage

These volumes persist even when containers are stopped/removed.

## Initialization Scripts

PostgreSQL will run all `.sql` files in `./postgres/` directory on first startup:
- `001_schema.sql` - Full production schema definition
- `003_seed_data.sql` - Initial seed data

## Health Checks

All services have health checks configured:
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- Qdrant: HTTP health endpoint

## Backup & Restore

### Backup PostgreSQL
```bash
docker exec shared_postgres pg_dump -U postgres nyx_venatrix > backup.sql
```

### Restore PostgreSQL
```bash
cat backup.sql | docker exec -i shared_postgres psql -U postgres nyx_venatrix
```

## Security Notes

- Change default passwords in production
- Use `.env` file for sensitive configuration
- Restrict network access in production deployments
