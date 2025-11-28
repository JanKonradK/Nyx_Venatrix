import { KdbClient } from './client';

export interface SalaryBenchmark {
    role: string;
    median: number;
    top_tier: number;
    currency: string;
}

export class SalaryFetcher {
    private kdb: KdbClient;

    constructor() {
        this.kdb = new KdbClient();
    }

    /**
     * Fetches real-time salary benchmark for a given role using KDB+ vector analytics.
     */
    async getBenchmark(role: string): Promise<SalaryBenchmark> {
        // q query to aggregate salary data
        const qQuery = `select avg salary, max salary from market_data where role like '${role}'`;

        const result = await this.kdb.execute(qQuery);

        return {
            role: role,
            median: result.p50,
            top_tier: result.p90,
            currency: result.currency
        };
    }
}
