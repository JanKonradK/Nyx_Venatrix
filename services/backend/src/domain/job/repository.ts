/**
 * Job repository - database operations for jobs
 */

import { Pool } from 'pg';
import { CreateJobParams, Job, JobStatus } from './entities';

export class JobRepository {
    constructor(private pool: Pool) { }

    async create(params: CreateJobParams, userId: string | null): Promise<Job> {
        const { url, source = 'webapp', notes } = params;
        const client = await this.pool.connect();

        try {
            await client.query('BEGIN');

            // 1. Ensure User Exists (Temporary Fix for Auth-less backend)
            let finalUserId = userId;
            if (!finalUserId) {
                const userResult = await client.query('SELECT id FROM users LIMIT 1');
                if (userResult.rows.length > 0) {
                    finalUserId = userResult.rows[0].id;
                } else {
                    const newUser = await client.query(
                        `INSERT INTO users (name, email) VALUES ('Default User', 'default@example.com') RETURNING id`
                    );
                    finalUserId = newUser.rows[0].id;
                }
            }

            // 2. Insert or Get Job Post
            // We use source_url as unique identifier for now, ideally canonical_url
            // checking if exists
            let jobPostId: string;
            const existingJob = await client.query(
                `SELECT id FROM job_posts WHERE source_url = $1`,
                [url]
            );

            if (existingJob.rows.length > 0) {
                jobPostId = existingJob.rows[0].id;
            } else {
                // Insert new job post
                const newJob = await client.query(
                    `INSERT INTO job_posts (source_url, description_raw)
                     VALUES ($1, $2)
                     RETURNING id`,
                    [url, notes || '']
                );
                jobPostId = newJob.rows[0].id;
            }

            // 3. Create Application
            // Check if already exists
            const existingApp = await client.query(
                `SELECT id, application_status FROM applications
                 WHERE user_id = $1 AND job_post_id = $2`,
                [finalUserId, jobPostId]
            );

            let appId: string;
            let status = 'queued';
            let createdAt = new Date();
            let updatedAt = new Date();

            if (existingApp.rows.length > 0) {
                appId = existingApp.rows[0].id;
                status = existingApp.rows[0].application_status;
                // We might want to reset status if it was failed? For now keep as is.
            } else {
                const newApp = await client.query(
                    `INSERT INTO applications (user_id, job_post_id, application_status)
                     VALUES ($1, $2, 'queued')
                     RETURNING id, application_status, created_at, updated_at`,
                    [finalUserId, jobPostId]
                );
                appId = newApp.rows[0].id;
                status = newApp.rows[0].application_status;
                createdAt = newApp.rows[0].created_at;
                updatedAt = newApp.rows[0].updated_at;
            }

            await client.query('COMMIT');

            // Return constructed Job entity
            return {
                id: appId, // We use Application ID as the "Job ID" for the backend API to track status
                url: url,
                title: 'Pending...',
                company_name: null,
                description: notes || null,
                status: status as any, // Cast to JobStatus
                user_id: finalUserId,
                created_at: createdAt,
                updated_at: updatedAt
            };

        } catch (e) {
            await client.query('ROLLBACK');
            throw e;
        } finally {
            client.release();
        }
    }

    async findById(id: string): Promise<Job | null> {
        // ID is expected to be Application ID
        const result = await this.pool.query(
            `SELECT
                a.id,
                jp.source_url as url,
                jp.job_title as title,
                c.name as company_name,
                jp.description_clean as description,
                a.application_status as status,
                a.user_id,
                a.created_at,
                a.updated_at,
                a.cost_estimated_total as cost_usd,
                a.tokens_input_total as tokens_input,
                a.tokens_output_total as tokens_output,
                a.failure_reason_detail as error_message
             FROM applications a
             JOIN job_posts jp ON a.job_post_id = jp.id
             LEFT JOIN companies c ON jp.company_id = c.id
             WHERE a.id = $1`,
            [id]
        );

        if (result.rows.length === 0) return null;
        return result.rows[0];
    }

    async updateStatus(id: string, status: JobStatus, metadata?: {
        cost_usd?: number;
        tokens_input?: number;
        tokens_output?: number;
        error_message?: string;
    }): Promise<Job> {
        // Map JobStatus to DB status
        // DB uses: 'queued', 'in_progress', 'submitted', 'failed', 'paused'
        // JobStatus uses: 'queued', 'in_progress', 'applied', 'failed', 'skipped'
        // 'applied' -> 'submitted'
        let dbStatus = status as string;
        if (status === 'applied') dbStatus = 'submitted';
        if (status === 'skipped') dbStatus = 'paused'; // or handled differently

        const client = await this.pool.connect();
        try {
            await client.query('BEGIN');

            const fields: string[] = ['application_status = $2', 'updated_at = NOW()'];
            const values: any[] = [id, dbStatus];
            let paramIndex = 3;

            if (metadata?.cost_usd !== undefined) {
                fields.push(`cost_estimated_total = COALESCE(cost_estimated_total, 0) + $${paramIndex++}`);
                values.push(metadata.cost_usd);
            }
            if (metadata?.tokens_input !== undefined) {
                fields.push(`tokens_input_total = COALESCE(tokens_input_total, 0) + $${paramIndex++}`);
                values.push(metadata.tokens_input);
            }
            if (metadata?.tokens_output !== undefined) {
                fields.push(`tokens_output_total = COALESCE(tokens_output_total, 0) + $${paramIndex++}`);
                values.push(metadata.tokens_output);
            }
            if (metadata?.error_message !== undefined) {
                fields.push(`failure_reason_detail = $${paramIndex++}`);
                values.push(metadata.error_message);
            }

            const result = await client.query(
                `UPDATE applications SET ${fields.join(', ')} WHERE id = $1 RETURNING *`,
                values
            );

            await client.query('COMMIT');

            // Re-fetch full object
            const updated = await this.findById(id);
            if (!updated) throw new Error("Failed to fetch updated job");
            return updated;

        } catch (e) {
            await client.query('ROLLBACK');
            throw e;
        } finally {
            client.release();
        }
    }

    async list(limit = 50, offset = 0): Promise<Job[]> {
        const result = await this.pool.query(
            `SELECT
                a.id,
                jp.source_url as url,
                jp.job_title as title,
                c.name as company_name,
                jp.description_clean as description,
                a.application_status as status,
                a.user_id,
                a.created_at,
                a.updated_at,
                a.cost_estimated_total as cost_usd,
                a.tokens_input_total as tokens_input,
                a.tokens_output_total as tokens_output,
                a.failure_reason_detail as error_message
             FROM applications a
             JOIN job_posts jp ON a.job_post_id = jp.id
             LEFT JOIN companies c ON jp.company_id = c.id
             ORDER BY a.created_at DESC
             LIMIT $1 OFFSET $2`,
            [limit, offset]
        );

        return result.rows;
    }
}
