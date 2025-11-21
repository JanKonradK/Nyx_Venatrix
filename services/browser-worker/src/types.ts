export interface Job {
    id: string;
    url: string;
    title?: string;
    company_name?: string;
    description?: string;
    status: 'queued' | 'in_progress' | 'applied' | 'failed' | 'skipped' | 'manual_only';
    created_at: Date;
    updated_at: Date;
    notes?: string;
}

export interface FormField {
    id: string;
    label: string;
    type: string;
    options?: string[];
    required?: boolean;
    value?: string | number | boolean;
    selector: string; // Added selector for Playwright
}

export interface FormSchema {
    fields: FormField[];
    submitSelector?: string;
}

export interface FormAnswers {
    [fieldId: string]: string | number | boolean;
}
