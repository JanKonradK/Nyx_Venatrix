import { URL } from 'url';

export type JobSourcePlatform =
    | "linkedin"
    | "indeed"
    | "company_site"
    | "ats_greenhouse"
    | "ats_workday"
    | "ats_lever"
    | "ats_other"
    | "unknown";

export type HandlingMode =
    | "auto_apply"
    | "manual_only"
    | "ignore";

export interface ResolvedApplicationSpec {
    originalUrl: string;
    canonicalUrl: string;
    sourcePlatform: JobSourcePlatform;
    handlingMode: HandlingMode;
    requiresManual: boolean;
    manualReason?: string;
}

export function resolveApplicationUrl(originalUrl: string): ResolvedApplicationSpec {
    let urlObj: URL;
    try {
        urlObj = new URL(originalUrl);
    } catch (e) {
        throw new Error('Invalid URL');
    }

    // Normalize: remove common tracking params
    const paramsToRemove = ['utm_source', 'utm_medium', 'utm_campaign', 'refId', 'trackingId'];
    paramsToRemove.forEach(p => urlObj.searchParams.delete(p));

    const canonicalUrl = urlObj.toString();
    const hostname = urlObj.hostname.toLowerCase();

    let sourcePlatform: JobSourcePlatform = 'unknown';
    let handlingMode: HandlingMode = 'auto_apply';
    let requiresManual = false;
    let manualReason = undefined;

    if (hostname.includes('linkedin.com')) {
        sourcePlatform = 'linkedin';
        // LinkedIn is tricky; often requires manual or easy apply which we skip for now
        // But if it's a direct link to a job, we might try.
        // For safety in V1, we might mark LinkedIn as manual_only unless we have a robust scraper.
        // The user wants to scrape everything, so we'll try to auto_apply if possible,
        // but usually LinkedIn requires login which we handle in worker.
        // However, "Easy Apply" is manual_only per policy.
        // We can't know if it's Easy Apply just from URL usually, so we assume auto_apply
        // and let the worker fail/switch to manual if it detects Easy Apply.
    } else if (hostname.includes('indeed.com')) {
        sourcePlatform = 'indeed';
    } else if (hostname.includes('greenhouse.io')) {
        sourcePlatform = 'ats_greenhouse';
    } else if (hostname.includes('workday.com') || hostname.includes('myworkdayjobs.com')) {
        sourcePlatform = 'ats_workday';
    } else if (hostname.includes('lever.co')) {
        sourcePlatform = 'ats_lever';
    } else {
        sourcePlatform = 'company_site';
    }

    return {
        originalUrl,
        canonicalUrl,
        sourcePlatform,
        handlingMode,
        requiresManual,
        manualReason
    };
}
