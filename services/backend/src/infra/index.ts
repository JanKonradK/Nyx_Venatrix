/**
 * Infrastructure module - database, config, logging
 */

import dotenv from 'dotenv';
import { Pool } from 'pg';

dotenv.config();

// Environment validation
export function validateEnvironment() {
    const required_vars = ['DATABASE_URL', 'GROK_API_KEY', 'AGENT_MODEL', 'EMBEDDING_MODEL'];
    const missing_vars = required_vars.filter(v => !process.env[v]);

    if (missing_vars.length > 0) {
        console.error(`❌ Missing required environment variables: ${missing_vars.join(', ')}`);
        console.error('Please check your .env file and ensure all required variables are set.');
        process.exit(1);
    }

    console.log('✓ All required environment variables validated');
}

// Database connection
export function createDatabasePool(): Pool {
    return new Pool({
        connectionString: process.env.DATABASE_URL
    });
}

// Redis configuration
export function getRedisConfig() {
    return {
        host: process.env.REDIS_HOST || 'redis',
        port: parseInt(process.env.REDIS_PORT || '6379', 10)
    };
}

// Configuration
export const config = {
    port: parseInt(process.env.PORT || '3000', 10),
    nodeEnv: process.env.NODE_ENV || 'development',
    agentUrl: process.env.AGENT_URL || 'http://agent:8000',
};
