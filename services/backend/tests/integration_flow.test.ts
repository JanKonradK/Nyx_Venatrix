// Simple integration test skeleton

import { AgentClient } from '../src/integrations/agent_client';

async function runIntegrationTest() {
    console.log('🚀 Running Integration Test: Backend -> Agent Flow');

    const agent = new AgentClient();

    // 1. Health Check
    console.log('1️⃣  Checking Agent Health...');
    const isHealthy = await agent.healthCheck();
    if (!isHealthy) {
        console.warn('⚠️  Agent service not reachable. Ensure the agent container is running.');
        console.warn('   Skipping live application test.');
        return;
    }
    console.log('✅ Agent is healthy.');

    // 2. Apply to Job
    console.log('2️⃣  Testing Apply Flow...');
    try {
        const result = await agent.applyToJob({
            url: 'https://example.com/job',
            effort_mode: 'LOW' // Use LOW effort for testing
        });
        console.log('✅ Apply request sent successfully.');
        console.log('   Result:', JSON.stringify(result, null, 2));
    } catch (e) {
        console.error('❌ Apply request failed:', e);
        process.exit(1);
    }

    console.log('🎉 Integration Test Complete!');
}

runIntegrationTest().catch(console.error);
