# Monitoring & Observability Setup

This document describes the monitoring and observability strategy for DeepApply.

## Current Implementation

### Logging
-   **Docker Compose Logs**: All services log to stdout/stderr, accessible via `docker logs`.
-   **Structured Logging**: Services should use structured JSON logs for easier parsing (future enhancement).

### Database Metrics
-   All job state transitions are persisted in Postgres.
-   Query the `jobs` table for historical analytics.

### Cost Tracking
-   Every job application tracks:
    -   `cost_usd`: Total LLM cost for this job.
    -   `tokens_input`: Input tokens used.
    -   `tokens_output`: Output tokens generated.

## Recommended Enhancements

### Prometheus + Grafana
For production deployments, integrate Prometheus metrics:

1.  **Add Prometheus exporter to each service**:
    -   Backend: Use `prom-client` (Node.js).
    -   Agent/Analytics: Use `prometheus-fastapi-instrumentator` (Python).

2.  **Metrics to track**:
    -   Request latency (API endpoints).
    -   Job queue depth (BullMQ).
    -   LLM API latency.
    -   Success/failure rates.
    -   Cost per hour/day.

3.  **Grafana Dashboards**:
    -   Real-time cost burn rate.
    -   Application success rate over time.
    -   Platform-specific performance.

### Error Tracking
-   **Sentry**: Integrate for error tracking and alerting.
-   **Alerts**: Set up Slack/Discord webhooks for critical errors (e.g., Agent crashes, database connection failures).

### Distributed Tracing
-   **OpenTelemetry**: Trace requests across Backend → Agent to identify bottlenecks.

## Quick Setup (Prometheus Example)

```yaml
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./infrastructure/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
  networks:
    - deepapply_net

grafana:
  image: grafana/grafana
  ports:
    - "3001:3000"
  networks:
    - deepapply_net
```

## Production Checklist

- [ ] Centralized logging (e.g., Loki, ELK stack)
- [ ] Metrics collection (Prometheus)
- [ ] Dashboards (Grafana)
- [ ] Error tracking (Sentry)
- [ ] Uptime monitoring (UptimeRobot, Pingdom)
- [ ] Backup strategy for Postgres
- [ ] Secrets management (Vault, AWS Secrets Manager)
