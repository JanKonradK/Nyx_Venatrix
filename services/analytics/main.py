import os
from datetime import datetime
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from fastapi import FastAPI, HTTPException

app = FastAPI(title="DeepApply Analytics API")

def get_db_connection():
    return psycopg2.connect(
        os.getenv('DATABASE_URL'),
        cursor_factory=RealDictCursor
    )

@app.get("/analytics/summary")
async def get_summary():
    """Get real-time analytics summary."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                COUNT(*) as total_jobs,
                COUNT(*) FILTER (WHERE status = 'applied') as successful_applications,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_applications,
                COALESCE(SUM(cost_usd), 0) as total_cost,
                COALESCE(AVG(cost_usd) FILTER (WHERE status = 'applied'), 0) as avg_cost_per_application,
                COALESCE(SUM(tokens_input), 0) as total_tokens_input,
                COALESCE(SUM(tokens_output), 0) as total_tokens_output
            FROM jobs
        """)

        result = cursor.fetchone()
        return dict(result)
    finally:
        cursor.close()
        conn.close()

@app.get("/analytics/trends")
async def get_trends():
    """Get daily trends for ML analysis."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as applications,
                SUM(cost_usd) as daily_cost,
                AVG(cost_usd) as avg_cost,
                COUNT(*) FILTER (WHERE status = 'applied') as success_count,
                COUNT(*) FILTER (WHERE status = 'failed') as failure_count
            FROM jobs
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)

        results = cursor.fetchall()
        return [dict(row) for row in results]
    finally:
        cursor.close()
        conn.close()

@app.get("/analytics/cost-by-platform")
async def get_cost_by_platform():
    """Analyze cost efficiency by platform."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                source_platform,
                COUNT(*) as total_jobs,
                AVG(cost_usd) as avg_cost,
                SUM(cost_usd) as total_cost,
                COUNT(*) FILTER (WHERE status = 'applied')::float / NULLIF(COUNT(*), 0) as success_rate
            FROM jobs
            WHERE source_platform != 'unknown'
            GROUP BY source_platform
            ORDER BY total_jobs DESC
        """)

        results = cursor.fetchall()
        return [dict(row) for row in results]
    finally:
        cursor.close()
        conn.close()

@app.get("/analytics/export")
async def export_for_ml():
    """Export data for ML training."""
    conn = get_db_connection()

    try:
        df = pd.read_sql_query("""
            SELECT
                created_at,
                source_platform,
                status,
                cost_usd,
                tokens_input,
                tokens_output,
                EXTRACT(HOUR FROM created_at) as hour_of_day,
                EXTRACT(DOW FROM created_at) as day_of_week
            FROM jobs
            WHERE created_at >= NOW() - INTERVAL '90 days'
        """, conn)

        return df.to_dict(orient='records')
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
