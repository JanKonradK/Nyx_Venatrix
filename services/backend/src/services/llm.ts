import OpenAI from 'openai';

// Initialize OpenAI client for Grok API
const openai = new OpenAI({
    apiKey: process.env.GROK_API_KEY,
    baseURL: 'https://api.grok.x.ai/v1'
});

import { searchProfile } from './rag';

export interface GenerateAnswersParams {
    jobDescription: string;
    formFields: {
        id: string;
        label: string;
        type: string;
    }[];
}

export async function generateAnswers(params: GenerateAnswersParams) {
    const { jobDescription, formFields } = params;

    // 1. Retrieve relevant profile information
    // We construct a query based on the job description and form fields
    const query = `Job: ${jobDescription.substring(0, 200)}... Fields: ${formFields.map(f => f.label).join(', ')}`;
    const profileSnippets = await searchProfile(query, 10);
    const userProfile = profileSnippets.join('\n\n');

    const prompt = `
    Job Description:
    ${jobDescription}

    User Profile:
    ${userProfile}

    Form Fields:
    ${JSON.stringify(formFields, null, 2)}

    Task:
    Generate the best answer for each form field based on the user profile and job description.
    Return a JSON object where keys are field IDs and values are the answers.
    If a field asks for salary, provide a realistic range or number based on the market.
    If a field is unknown, leave it empty or provide a safe default.
  `;

    try {
        const completion = await openai.chat.completions.create({
            model: process.env.AGENT_MODEL || 'grok-beta',
            messages: [
                { role: 'system', content: 'You are a helpful assistant.' },
                { role: 'user', content: prompt }
            ],
            response_format: { type: 'json_object' }
        });

        const content = completion.choices[0].message.content;
        return JSON.parse(content || '{}');
    } catch (error: any) {
        console.error('Error generating answers:', error);
        return {};
    }
}
