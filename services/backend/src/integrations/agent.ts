/**
 * Agent integration - communicates with Python agent service
 */

import axios from 'axios';

export interface AgentJobRequest {
    url: string;
    keywords?: string[];
}

export interface AgentJobResponse {
    status: string;
    data: {
        output: string;
        cost_usd: number;
        tokens_input: number;
        tokens_output: number;
        error?: string;
    };
}

export class AgentClient {
    private baseURL: string;

    constructor() {
        this.baseURL = process.env.AGENT_URL || 'http://agent:8000';
    }

    async applyToJob(jobRequest: AgentJobRequest): Promise<AgentJobResponse['data']> {
        try {
            const response = await axios.post<AgentJobResponse>(
                `${this.baseURL}/apply`,
                jobRequest,
                { timeout: 300000 } // 5 minute timeout for long-running browser automation
            );

            return response.data.data;
        } catch (error: any) {
            console.error('Agent service error:', error.message);
            throw new Error(`Agent service failed: ${error.message}`);
        }
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
