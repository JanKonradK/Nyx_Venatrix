/**
 * Job domain module
 * Handles job entities, parsing, and state machine
 */

export enum JobStatus {
    QUEUED = 'queued',
    IN_PROGRESS = 'in_progress',
    APPLIED = 'applied',
    FAILED = 'failed',
    SKIPPED = 'skipped'
}

export interface Job {
    id: string;
    url: string;
    title: string | null;
    company_name: string | null;
    description: string | null;
    status: JobStatus;
    user_id: string | null;
    created_at: Date;
    updated_at: Date;
    // Optional / Metadata
    cost_usd?: number;
    tokens_input?: number;
    tokens_output?: number;
    error_message?: string;
}

export interface CreateJobParams {
    url: string;
    source?: string;
    notes?: string;
}

export class JobStateMachine {
    static canTransition(from: JobStatus, to: JobStatus): boolean {
        const allowedTransitions: Record<JobStatus, JobStatus[]> = {
            [JobStatus.QUEUED]: [JobStatus.IN_PROGRESS, JobStatus.SKIPPED],
            [JobStatus.IN_PROGRESS]: [JobStatus.APPLIED, JobStatus.FAILED],
            [JobStatus.APPLIED]: [],
            [JobStatus.FAILED]: [JobStatus.QUEUED], // Allow retry
            [JobStatus.SKIPPED]: []
        };

        return allowedTransitions[from]?.includes(to) ?? false;
    }
}
