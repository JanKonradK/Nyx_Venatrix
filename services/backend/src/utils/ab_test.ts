export class ABTest {
    private static experiments: Record<string, number> = {
        'USE_NEW_AGENT_MODEL': 0.5, // 50% chance
        'AGGRESSIVE_RETRY': 0.2,    // 20% chance
    };

    static isEnabled(experiment: string, userId: string): boolean {
        if (!this.experiments[experiment]) return false;

        // Simple deterministic hash for consistent assignment
        let hash = 0;
        for (let i = 0; i < userId.length; i++) {
            hash = ((hash << 5) - hash) + userId.charCodeAt(i);
            hash |= 0;
        }

        const normalized = Math.abs(hash) % 100 / 100;
        return normalized < this.experiments[experiment];
    }

    static logExposure(experiment: string, userId: string, variant: 'CONTROL' | 'VARIANT') {
        console.log(`[AB_TEST] User ${userId} exposed to ${experiment}: ${variant}`);
        // In a real system, send to analytics
    }
}
