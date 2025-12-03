/**
 * Queue management module
 */

import { Job as BullJob, Queue, Worker } from 'bullmq';
import { JobService, JobStatus } from '../domain/job';
import { AgentClient } from '../integrations';

type JobQueuePayload = {
    job_id: string;
    url: string;
};

export class JobQueueManager {
    private queue: Queue<JobQueuePayload>;
    private worker: Worker<JobQueuePayload>;

    constructor(
        private jobService: JobService,
        private agentClient: AgentClient,
        redisConfig: { host: string; port: number }
    ) {
        // Create queue
        this.queue = new Queue<JobQueuePayload>('job-processing', {
            connection: redisConfig
        });

        // Create worker
        this.worker = new Worker<JobQueuePayload>(
            'job-processing',
            async (job: BullJob<JobQueuePayload>) => await this.processJob(job),
            { connection: redisConfig }
        );

        this.setupEventHandlers();
    }

    private async processJob(bullJob: BullJob<JobQueuePayload>) {
        const { job_id, url } = bullJob.data;

        console.log(`Processing job ${job_id}: ${url}`);

        try {
            // Update status to in_progress
            await this.jobService.updateStatus(job_id, JobStatus.IN_PROGRESS);

            // Call agent service
            const result = await this.agentClient.applyToJob({
                url,
                keywords: []
            });

            // Check if agent returned an error
            if (result.error) {
                await this.jobService.updateStatus(job_id, JobStatus.FAILED, {
                    error_message: result.error,
                    cost_usd: result.cost_usd,
                    tokens_input: result.tokens_input,
                    tokens_output: result.tokens_output
                });
                return;
            }

            // Update status to applied with cost data
            await this.jobService.updateStatus(job_id, JobStatus.APPLIED, {
                cost_usd: result.cost_usd,
                tokens_input: result.tokens_input,
                tokens_output: result.tokens_output
            });

            console.log(`✅ Job ${job_id} completed successfully. Cost: $${result.cost_usd}`);
        } catch (error: any) {
            console.error(`❌ Job ${job_id} failed:`, error.message);

            await this.jobService.updateStatus(job_id, JobStatus.FAILED, {
                error_message: error.message,
                cost_usd: 0
            });
        }
    }

    private setupEventHandlers() {
        this.worker.on('completed', (job) => {
            console.log(`Job ${job.id} completed`);
        });

        this.worker.on('failed', (job, err) => {
            console.error(`Job ${job?.id} failed:`, err.message);
        });
    }

    getQueue(): Queue<JobQueuePayload> {
        return this.queue;
    }

    async close() {
        await this.worker.close();
        await this.queue.close();
    }
}
