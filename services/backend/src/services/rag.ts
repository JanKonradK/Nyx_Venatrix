import OpenAI from 'openai';
import { Pool } from 'pg';

const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
});

const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
});

export async function embedText(text: string): Promise<number[]> {
    const response = await openai.embeddings.create({
        model: process.env.EMBEDDING_MODEL || 'text-embedding-3-small',
        input: text,
    });
    return response.data[0].embedding;
}

export async function storeEmbedding(text: string, source: string, metadata: any = {}) {
    const embedding = await embedText(text);
    const client = await pool.connect();
    try {
        await client.query(
            `INSERT INTO embeddings (content, embedding, source, metadata) VALUES ($1, $2, $3, $4)`,
            [text, JSON.stringify(embedding), source, JSON.stringify(metadata)]
        );
    } finally {
        client.release();
    }
}

export async function searchProfile(query: string, limit: number = 5): Promise<string[]> {
    const embedding = await embedText(query);
    const client = await pool.connect();
    try {
        // Using pgvector's <=> operator for cosine distance (lower is better)
        // We want the closest matches, so we order by distance ASC
        const res = await client.query(
            `SELECT content FROM embeddings ORDER BY embedding <=> $1 LIMIT $2`,
            [JSON.stringify(embedding), limit]
        );
        return res.rows.map((row) => row.content);
    } finally {
        client.release();
    }
}
