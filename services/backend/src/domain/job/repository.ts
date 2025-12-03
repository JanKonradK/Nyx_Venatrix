/**
 * Job repository - database operations for jobs
 */

import { Pool } from 'pg';
import { CreateJobParams, Job, JobStatus } from './entities';

export class JobRepository {
    constructor(private pool: Pool) { }

    async create(params: CreateJobParams): Promise<Job> {
        const { url, source = 'webapp', notes } = params;

        const result = await this.pool.query(
            `INSERT INTO jobs(original_url, canonical_url, source, source_platform, status)
             VALUES($1, $1, $2, 'unknown', 'queued')
             RETURNING *`,
            [url, source]
        );

        return result.rows[0];
    }

    async findById(id: string): Promise<Job | null> {
        const result = await this.pool.query(
            'SELECT * FROM jobs WHERE id = $1',
            [id]
        );

        return result.rows[0] || null;
    }

    async updateStatus(id: string, status: JobStatus, metadata?: {
        cost_usd?: number;
        tokens_input?: number;
        tokens_output?: number;
        error_message?: string;
    }): Promise<Job> {
        const fields: string[] = ['status = $2', 'updated_at = NOW()'];
        const values: any[] = [id, status];
        let paramIndex = 3;

        if (metadata?.cost_usd !== undefined) {
            fields.push(`cost_usd = $${paramIndex++}`);
            values.push(metadata.cost_usd);
        }
        if (metadata?.tokens_input !== undefined) {
            fields.push(`tokens_input = $${paramIndex++}`);
            values.push(metadata.tokens_input);
        }
        if (metadata?.tokens_output !== undefined) {
            fields.push(`tokens_output = $${paramIndex++}`);
            values.push(metadata.tokens_output);
        }
        if (metadata?.error_message !== undefined) {
            fields.push(`error_message = $${paramIndex++}`);
            values.push(metadata.error_message);
        }

        const result = await this.pool.query(
            `UPDATE jobs SET ${fields.join(', ')} WHERE id = $1 RETURNING *`,
            values
        );

        return result.rows[0];
    }

    async list(limit = 50, offset = 0): Promise<Job[]> {
        const result = await this.pool.query(
            'SELECT * FROM jobs ORDER BY created_at DESC LIMIT $1 OFFSET $2',
            [limit, offset]
        );

        return result.rows;
    }
}
