import OpenAI from 'openai';

// Initialize OpenAI client pointing to Grok API (if compatible) or just use OpenAI for now as placeholder
// The user specified Grok 4.1 Fast. Assuming it has an OpenAI-compatible API.
// If not, we'd use a custom fetch. For now, assuming standard OpenAI SDK compatibility.
const openai = new OpenAI({
    apiKey: process.env.GROK_API_KEY || 'dummy',
    baseURL: 'https://api.grok.x.ai/v1' // Hypothetical URL, adjust as needed
});

export interface GenerateAnswersParams {
    jobDescription: string;
    formFields: {
        id: string;
        label: string;
        type: string;
    }[];
    userProfile: string; // Retrieved from RAG
}

export async function generateAnswers(params: GenerateAnswersParams) {
    const { jobDescription, formFields, userProfile } = params;

    const prompt = `
    You are DeepApply, an expert job application agent.

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
            model: 'grok-beta', // or whatever the model name is
            messages: [
                { role: 'system', content: 'You are a helpful assistant.' },
                { role: 'user', content: prompt }
            ],
            response_format: { type: 'json_object' }
        });

        const content = completion.choices[0].message.content;
        return JSON.parse(content || '{}');
    } catch (error) {
        console.error('Error generating answers:', error);
        return {};
    }
}
