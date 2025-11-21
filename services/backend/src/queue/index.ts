import { Job, Queue, Worker } from 'bullmq';

const connection = {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379')
};

export const jobQueue = new Queue('job_application', { connection });

// Worker will be initialized in the main entry point or a separate worker process
// For now, we just export the setup function
export const setupWorker = () => {
    const worker = new Worker('job_application', async (job: Job) => {
        console.log(`Processing job ${job.id} with data:`, job.data);
        // TODO: Call the actual processing logic here
        // await processJob(job.data.jobId);
    }, { connection });

    worker.on('completed', (job: Job) => {
        console.log(`Job ${job.id} completed!`);
    });

    worker.on('failed', (job: Job | undefined, err: Error) => {
        console.log(`Job ${job?.id} failed with ${err.message}`);
    });

    return worker;
};
