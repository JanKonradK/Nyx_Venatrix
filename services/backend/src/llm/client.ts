/**
 * LLM module - Grok and OpenAI client wrappers
 */

import OpenAI from 'openai';

export class LLMClient {
    private grokClient: OpenAI;
    private openaiClient: OpenAI;

    constructor() {
        // Grok client
        this.grokClient = new OpenAI({
            apiKey: process.env.GROK_API_KEY!,
            baseURL: 'https://api.grok.x.ai/v1'
        });

        // OpenAI client (for embeddings)
        this.openaiClient = new OpenAI({
            apiKey: process.env.OPENAI_API_KEY!
        });
    }

    async chat(prompt: string, systemPrompt?: string): Promise<string> {
        const completion = await this.grokClient.chat.completions.create({
            model: process.env.AGENT_MODEL || 'grok-beta',
            messages: [
                { role: 'system', content: systemPrompt || 'You are a helpful assistant.' },
                { role: 'user', content: prompt }
            ],
        });

        return completion.choices[0].message.content || '';
    }

    async chatJSON(prompt: string, systemPrompt?: string): Promise<any> {
        const completion = await this.grokClient.chat.completions.create({
            model: process.env.AGENT_MODEL || 'grok-beta',
            messages: [
                { role: 'system', content: systemPrompt || 'You are a helpful assistant.' },
                { role: 'user', content: prompt }
            ],
            response_format: { type: 'json_object' }
        });

        const content = completion.choices[0].message.content || '{}';
        return JSON.parse(content);
    }

    async embed(text: string): Promise<number[]> {
        const response = await this.openaiClient.embeddings.create({
            model: process.env.EMBEDDING_MODEL || 'text-embedding-3-small',
            input: text,
        });

        return response.data[0].embedding;
    }
}
