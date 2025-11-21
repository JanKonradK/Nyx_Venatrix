/**
 * Job service - orchestrates job-related business logic
 */

import { Queue } from 'bullmq';
import { CreateJobParams, Job, JobStateMachine, JobStatus } from './entities';
import { JobRepository } from './repository';

export class JobService {
    constructor(
        private repository: JobRepository,
        private jobQueue: Queue
    ) { }

    async createAndQueue(params: CreateJobParams): Promise<{ job_id: number; status: string }> {
        // Create job in database
        const job = await this.repository.create(params);

        // Add to processing queue
        await this.jobQueue.add('process_job', {
            job_id: job.id,
            url: job.original_url
        });

        return {
            job_id: job.id,
            status: 'queued'
        };
    }

    async getById(id: number): Promise<Job | null> {
        return this.repository.findById(id);
    }

    async updateStatus(
        id: number,
        newStatus: JobStatus,
        metadata?: Parameters<JobRepository['updateStatus']>[2]
    ): Promise<Job> {
        const job = await this.repository.findById(id);
        if (!job) {
            throw new Error(`Job ${id} not found`);
        }

        // Validate state transition
        if (!JobStateMachine.canTransition(job.status as JobStatus, newStatus)) {
            throw new Error(
                `Invalid state transition from ${job.status} to ${newStatus}`
            );
        }

        return this.repository.updateStatus(id, newStatus, metadata);
    }

    async list(limit?: number, offset?: number): Promise<Job[]> {
        return this.repository.list(limit, offset);
    }
}
