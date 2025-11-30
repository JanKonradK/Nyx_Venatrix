export interface Profile {
    id: string;
    userId: string;
    fullName: string;
    email: string;
    phone?: string;
    location?: string;
    linkedinUrl?: string;
    portfolioUrl?: string;
    skills: string[];
    experience: Experience[];
    education: Education[];
}

export interface Experience {
    company: string;
    role: string;
    startDate: Date;
    endDate?: Date;
    description: string;
}

export interface Education {
    institution: string;
    degree: string;
    year: number;
}

import { SalaryFetcher } from '../../integrations/kdb/salary_fetcher';

export class ProfileService {
    private salaryFetcher: SalaryFetcher;

    constructor() {
        this.salaryFetcher = new SalaryFetcher();
    }

    /**
     * Retrieves a user profile.
     * Currently returns a mock profile as the database schema for profiles is not yet finalized.
     */
    async getProfile(userId: string): Promise<Profile | null> {
        // Mock profile for development/testing
        return {
            id: 'mock-profile-id',
            userId: userId,
            fullName: 'Jan Konrad',
            email: 'jan@example.com',
            skills: ['TypeScript', 'Python', 'React'],
            experience: [],
            education: []
        };
    }

    /**
     * Updates a user profile.
     * Currently a no-op.
     */
    async updateProfile(userId: string, data: Partial<Profile>): Promise<void> {
        console.log(`[ProfileService] Updating profile for ${userId}`, data);
    }
}
