import { FastifyInstance } from 'fastify';
import { Pool } from 'pg';
import { jobQueue } from '../queue';

const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

interface ApplyJobBody {
    url: string;
    notes?: string;
    source?: string;
}

interface JobParams {
    id: string;
}

export default async function jobRoutes(fastify: FastifyInstance) {

    // POST /jobs/apply
    fastify.post<{ Body: ApplyJobBody }>('/jobs/apply', async (request, reply) => {
        const { url, notes, source = 'webapp' } = request.body;

        if (!url) {
            return reply.code(400).send({ error: 'URL is required' });
        }

        const client = await pool.connect();
        try {
            // 1. Insert into DB
            const res = await client.query(
                `INSERT INTO jobs (original_url, canonical_url, source, source_platform, status)
         VALUES ($1, $1, $2, 'unknown', 'queued')
         RETURNING id`,
                [url, source]
            );
            const jobId = res.rows[0].id;

            // 2. Add to Queue
            await jobQueue.add('process_job', { jobId, url });

            return { jobId, status: 'queued' };
        } catch (err) {
            fastify.log.error(err);
            return reply.code(500).send({ error: 'Internal Server Error' });
        } finally {
            client.release();
        }
    });

    // GET /jobs/:id
    fastify.get<{ Params: JobParams }>('/jobs/:id', async (request, reply) => {
        const { id } = request.params;
        const client = await pool.connect();
        try {
            const res = await client.query('SELECT * FROM jobs WHERE id = $1', [id]);
            if (res.rows.length === 0) {
                return reply.code(404).send({ error: 'Job not found' });
            }
            return res.rows[0];
        } finally {
            client.release();
        }
    });
}
