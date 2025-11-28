export enum ApplicationStatus {
    PENDING = 'PENDING',
    APPLIED = 'APPLIED',
    REJECTED = 'REJECTED',
    INTERVIEW = 'INTERVIEW',
    OFFER = 'OFFER'
}

export interface Application {
    id: string;
    jobId: string;
    userId: string;
    status: ApplicationStatus;
    appliedAt: Date;
    lastUpdated: Date;
    resumeVersion: string;
    coverLetter?: string;
    notes?: string;
}

export interface ApplicationRepository {
    save(application: Application): Promise<void>;
    findById(id: string): Promise<Application | null>;
    findByUserId(userId: string): Promise<Application[]>;
}
