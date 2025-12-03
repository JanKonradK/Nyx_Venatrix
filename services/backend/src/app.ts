/**
 * Nyx Venatrix Backend
 * Orchestrates agents, manages state, and exposes HTTP API
 */

import cors from '@fastify/cors';
import Fastify from 'fastify';
import { JobRepository, JobService } from './domain/job';
import { config, createDatabasePool, getRedisConfig, validateEnvironment } from './infra';
import { AgentClient, TelegramBot } from './integrations';
import { JobQueueManager } from './queues';

// Validate environment on startup
validateEnvironment();

// Initialize Fastify
const fastify = Fastify({
    logger: true
});

// CORS
fastify.register(cors, {
    origin: process.env.CORS_ORIGIN || '*' // TODO: Restrict in production
});

// Infrastructure
const dbPool = createDatabasePool();
const redisConfig = getRedisConfig();

// Domain layer
const jobRepository = new JobRepository(dbPool);

//Integrations
const agentClient = new AgentClient();

// Queue management (needs to be initialized after jobService)
let queueManager: JobQueueManager;

// Initialize queue after jobService
const initializeQueue = (jobService: JobService) => {
    queueManager = new JobQueueManager(jobService, agentClient, redisConfig);
    return queueManager.getQueue();
};

// Service layer
const jobService = new JobService(jobRepository);

// Now initialize real queue
const realQueue = initializeQueue(jobService);
jobService.setQueue(realQueue);

// Telegram bot
const telegramBot = new TelegramBot(jobService);

// Routes
fastify.get('/health', async () => {
    try {
        const client = await dbPool.connect();
        await client.query('SELECT 1');
        client.release();

        const agentHealthy = await agentClient.healthCheck();

        return {
            status: 'ok',
            services: {
                database: 'connected',
                agent: agentHealthy ? 'healthy' : 'unavailable',
                queue: 'running'
            }
        };
    } catch (err) {
        fastify.log.error(err);
        return {
            status: 'error',
            database: 'disconnected'
        };
    }
});

// Job routes
fastify.post<{ Body: { url: string; notes?: string; source?: string } }>(
    '/jobs/apply',
    async (request, reply) => {
        const { url, notes, source } = request.body;

        if (!url) {
            return reply.code(400).send({ error: 'URL is required' });
        }

        try {
            const result = await jobService.createAndQueue({ url, notes, source });
            return result;
        } catch (err: any) {
            fastify.log.error(err);
            return reply.code(500).send({ error: err.message });
        }
    }
);

fastify.get<{ Params: { id: string } }>(
    '/jobs/:id',
    async (request, reply) => {
        const { id } = request.params;

        try {
            const job = await jobService.getById(id);

            if (!job) {
                return reply.code(404).send({ error: 'Job not found' });
            }

            return job;
        } catch (err: any) {
            fastify.log.error(err);
            return reply.code(500).send({ error: err.message });
        }
    }
);

fastify.get('/jobs', async (request) => {
    try {
        const jobs = await jobService.list(50, 0);
        return { jobs };
    } catch (err: any) {
        fastify.log.error(err);
        return { error: err.message };
    }
});

// Start server
const start = async () => {
    try {
        await fastify.listen({ port: config.port, host: '0.0.0.0' });
        console.log(`🚀 Backend server listening on http://0.0.0.0:${config.port}`);

        // Start Telegram bot
        await telegramBot.launch();

        console.log('✅ Nyx Venatrix Backend ready!');
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
};

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down gracefully...');
    await telegramBot.stop();
    await queueManager.close();
    await dbPool.end();
    process.exit(0);
});

start();
