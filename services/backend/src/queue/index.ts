import { Job, Queue, Worker } from 'bullmq';
import { Pool } from 'pg';

const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

const connection = {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379')
};

export const jobQueue = new Queue('job_application', { connection });

// Worker initialized in main entry point
export const setupWorker = () => {
    const worker = new Worker('job_application', async (job: Job) => {
        console.log(`Processing job ${job.id} with data:`, job.data);
        const { url } = job.data;

        try {
            // Call Agent Service
            // Use 'agent' hostname as defined in docker-compose
            const agentUrl = process.env.AGENT_URL || 'http://agent:8000';
            console.log(`Delegating job ${job.id} to agent at ${agentUrl}...`);

            // Import axios dynamically or use fetch if preferred, but axios is in deps.
            // Since this is inside a function, I should import axios at top level.
            // But I can't change top level imports with this tool easily if I don't view the whole file.
            // I'll assume axios is imported or I'll use dynamic import or global fetch (Node 18+).
            // Package.json has axios. Let's check if I can add the import.
            // Actually, I'll use the global fetch if available or require axios.
            // To be safe and clean, I should have added "import axios from 'axios';" at the top.
            // Let's try to use require for now to avoid messing up imports if I can't see them all (I saw them, but replace_file_content is local).
            // Wait, I viewed the file, I know line 1 has imports.
            // I will use a separate tool call to add the import if needed, but I can just use require here or assume it's fine.
            // Actually, I'll use `const axios = require('axios');` inside the function or just use `fetch`.
            // Node 18 has fetch.

            const response = await fetch(`${agentUrl}/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, keywords: [] })
            });

            if (!response.ok) {
                throw new Error(`Agent service returned ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log(`Agent response for job ${job.id}:`, result);

            // Update job with cost data
            const client = await pool.connect();
            try {
                await client.query(
                    `UPDATE jobs
                     SET status = 'applied',
                         cost_usd = $1,
                         tokens_input = $2,
                         tokens_output = $3
                     WHERE id = $4`,
                    [result.cost_usd || 0, result.tokens_input || 0, result.tokens_output || 0, job.id]
                );
            } finally {
                client.release();
            }

        } catch (error: any) {
            console.error(`Failed to process job ${job.id} via agent:`, error.message);
            throw error;
        }
    }, { connection });

    worker.on('completed', (job: Job) => {
        console.log(`Job ${job.id} completed!`);
    });

    worker.on('failed', (job: Job | undefined, err: Error) => {
        console.log(`Job ${job?.id} failed with ${err.message}`);
    });

    return worker;
};
