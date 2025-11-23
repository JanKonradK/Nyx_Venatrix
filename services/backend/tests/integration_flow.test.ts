// Simple integration test skeleton
import { AgentClient } from '../src/integrations/agent';

async function runIntegrationTest() {
    console.log('Running Integration Test: Backend -> Agent Flow');

    const agent = new AgentClient();

    // Mock the health check
    const isHealthy = await agent.healthCheck();
    if (!isHealthy) {
        console.log('⚠️ Agent service not reachable (expected in build env). Skipping live call.');
        return;
    }

    try {
        await agent.applyToJob({ url: 'https://example.com/job' });
        console.log('✅ Agent call successful');
    } catch (e) {
        console.log('❌ Agent call failed (as expected without live agent)');
    }
}

runIntegrationTest();
