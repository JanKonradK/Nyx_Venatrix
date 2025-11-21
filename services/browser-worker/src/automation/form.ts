import { Page } from 'playwright';
import { FormAnswers, FormField, FormSchema } from '../types';

export async function extractFormSchema(page: Page): Promise<FormSchema> {
    // Heuristic-based form extraction
    // This is a simplified version. In a real app, this would be much more complex.

    const fields: FormField[] = [];

    // Find all inputs, selects, and textareas
    const elements = await page.$$('input, select, textarea');

    for (const element of elements) {
        const isVisible = await element.isVisible();
        if (!isVisible) continue;

        const type = await element.getAttribute('type') || await element.evaluate(el => el.tagName.toLowerCase());
        const id = await element.getAttribute('id') || await element.getAttribute('name') || `field_${Math.random().toString(36).substring(7)}`;
        const name = await element.getAttribute('name');
        const labelElement = await page.$(`label[for="${id}"]`);
        let label = labelElement ? await labelElement.innerText() : '';

        if (!label && name) {
            label = name; // Fallback
        }

        // Get options for select
        let options: string[] | undefined;
        if (type === 'select') {
            options = await element.$$eval('option', opts => opts.map(o => o.innerText));
        }

        // Generate a unique selector
        let selector = '';
        if (await element.getAttribute('id')) {
            selector = `#${await element.getAttribute('id')}`;
        } else if (await element.getAttribute('name')) {
            selector = `[name="${await element.getAttribute('name')}"]`;
        } else {
            // Fallback to some other attribute or path (simplified)
            selector = type;
        }

        fields.push({
            id,
            label: label.trim(),
            type,
            options,
            selector
        });
    }

    // Find submit button
    const submitButton = await page.$('button[type="submit"], input[type="submit"]');
    let submitSelector = '';
    if (submitButton) {
        // Try to find a good selector for the submit button
        const id = await submitButton.getAttribute('id');
        if (id) submitSelector = `#${id}`;
        else submitSelector = 'button[type="submit"]';
    }

    return { fields, submitSelector };
}

export async function fillForm(page: Page, schema: FormSchema, answers: FormAnswers): Promise<void> {
    for (const field of schema.fields) {
        const answer = answers[field.id];
        if (answer === undefined || answer === null || answer === '') continue;

        try {
            const element = page.locator(field.selector);

            if (field.type === 'select' || field.type === 'select-one') {
                await element.selectOption({ label: String(answer) }).catch(() => element.selectOption({ value: String(answer) }));
            } else if (field.type === 'checkbox') {
                if (answer) await element.check();
                else await element.uncheck();
            } else if (field.type === 'radio') {
                await element.check();
            } else if (field.type === 'file') {
                // Handle file upload - assuming answer is a path
                // await element.setInputFiles(String(answer));
                console.log(`Skipping file upload for ${field.label} (not implemented yet)`);
            } else {
                await element.fill(String(answer));
            }
        } catch (e) {
            console.warn(`Failed to fill field ${field.label} (${field.id}):`, e);
        }
    }
}

export async function submitForm(page: Page, schema: FormSchema): Promise<void> {
    if (schema.submitSelector) {
        await page.click(schema.submitSelector);
    } else {
        console.warn('No submit selector found.');
    }
}
