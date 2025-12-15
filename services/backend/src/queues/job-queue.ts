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
                job_post_id: job_id,
                mode: 'review' // Default mode
            });

            // Since agent is async (Ray), we just confirm it's queued
            console.log(`✅ Job ${job_id} queued in agent: ${result.status}`);

            // We leave the job as IN_PROGRESS or set to APPLIED if we consider handoff as 'applied'
            // For now, let's keep it IN_PROGRESS until a webhook or polling updates it, 
            // or just assume it is being handled. 
            // The frontend should check Application status separately.

        } catch (error: any) {
            console.error(`❌ Job ${job_id} failed to queue:`, error.message);

            await this.jobService.updateStatus(job_id, JobStatus.FAILED, {
                error_message: error.message
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
