/**
 * Agent integration - communicates with Python agent service
 */

import axios from 'axios';

export interface AgentJobRequest {
    job_post_id: string;
    mode: 'review' | 'auto';
}

export interface AgentJobResponse {
    job_post_id: string;
    status: string;
    // Data field might be optional or different in new response
    data?: any;
}

export class AgentClient {
    private baseURL: string;

    constructor() {
        this.baseURL = process.env.AGENT_URL || 'http://agent:8000';
    }

    private failures = 0;
    private lastFailureTime = 0;
    private readonly FAILURE_THRESHOLD = 3;
    private readonly RESET_TIMEOUT = 60000; // 1 minute

    async applyToJob(jobRequest: AgentJobRequest): Promise<AgentJobResponse> {
        if (this.isOpen()) {
            throw new Error('Circuit breaker is OPEN: Agent service is down.');
        }

        try {
            const response = await axios.post<AgentJobResponse>(
                `${this.baseURL}/apply`,
                jobRequest,
                { timeout: 300000 } // 5 minute timeout
            );

            this.reset();
            return response.data;
        } catch (error: any) {
            this.recordFailure();
            console.error('Agent service error:', error.message);
            throw new Error(`Agent service failed: ${error.message}`);
        }
    }

    private isOpen(): boolean {
        if (this.failures >= this.FAILURE_THRESHOLD) {
            if (Date.now() - this.lastFailureTime > this.RESET_TIMEOUT) {
                return false; // Half-open (allow one try)
            }
            return true;
        }
        return false;
    }

    private recordFailure() {
        this.failures++;
        this.lastFailureTime = Date.now();
    }

    private reset() {
        this.failures = 0;
        this.lastFailureTime = 0;
    }

    async ingestKnowledgeBase(): Promise<void> {
        await axios.post(`${this.baseURL}/ingest`);
    }

    async healthCheck(): Promise<boolean> {
        try {
            const response = await axios.get(`${this.baseURL}/health`);
            return response.data.status === 'active';
        } catch {
            return false;
        }
    }
}
