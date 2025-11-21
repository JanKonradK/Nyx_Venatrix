import dotenv from 'dotenv';
import Fastify, { FastifyReply, FastifyRequest } from 'fastify';
import { Pool } from 'pg';

dotenv.config();

// Validate required environment variables
const required_env_vars = ['DATABASE_URL', 'GROK_API_KEY', 'AGENT_MODEL', 'EMBEDDING_MODEL'];
const missing_vars = required_env_vars.filter(v => !process.env[v]);
if (missing_vars.length > 0) {
    console.error(`❌ Missing required environment variables: ${missing_vars.join(', ')}`);
    console.error('Please check your .env file and ensure all required variables are set.');
    process.exit(1);
}
console.log('✓ All required environment variables validated');


const fastify = Fastify({
    logger: true
});

// Database connection
const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

// Health check
fastify.get('/health', async (request: FastifyRequest, reply: FastifyReply) => {
    try {
        const client = await pool.connect();
        await client.query('SELECT 1');
        client.release();
        return { status: 'ok', db: 'connected' };
    } catch (err) {
        fastify.log.error(err);
        return reply.code(500).send({ status: 'error', db: 'disconnected' });
    }
});

import { setupWorker } from './queue';
import jobRoutes from './routes/jobs';

// Register routes
fastify.register(jobRoutes);

// Start worker
setupWorker();

// Start server
const start = async () => {
    try {
        await fastify.listen({ port: 3000, host: '0.0.0.0' });
        console.log('Server listening on http://0.0.0.0:3000');
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
};

start();
