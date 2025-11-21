import { Job, Worker } from 'bullmq';
import dotenv from 'dotenv';
import { Pool } from 'pg';
import { chromium } from 'playwright-extra';
import stealth from 'puppeteer-extra-plugin-stealth';

dotenv.config();

// Add stealth plugin
chromium.use(stealth());

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

const connection = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379')
};

async function processJob(job: Job) {
  const { jobId, url } = job.data;
  console.log(`Processing job ${jobId} for URL: ${url}`);

  const client = await pool.connect();
  try {
    // Update status to in_progress
    await client.query('UPDATE jobs SET status = $1 WHERE id = $2', ['in_progress', jobId]);

    // Launch browser
    const browser = await chromium.launch({ headless: true }); // Set to false for debugging
    const page = await browser.newPage();

    // Go to URL
    console.log(`Navigating to ${url}...`);
    await page.goto(url, { waitUntil: 'networkidle' });

    // Take screenshot
    const screenshotPath = `/app/screenshots/${jobId}_initial.png`;
    // Ensure directory exists (in real app)
    // await page.screenshot({ path: screenshotPath });

    // Scrape basic info (Title, Company, etc.)
    const title = await page.title();
    const content = await page.content();

    console.log(`Scraped title: ${title} `);

    // Update job with scraped data
    await client.query(
      `UPDATE jobs
       SET title = $1, description = $2, status = 'applied'
       WHERE id = $3`,
      [title, 'Scraped content placeholder', jobId]
    );

    await browser.close();
    console.log(`Job ${jobId} completed.`);
  } catch (err: any) {
    console.error(`Job ${jobId} failed: `, err);
    await client.query('UPDATE jobs SET status = $1, notes = $2 WHERE id = $3', ['failed', err.message, jobId]);
    throw err;
  } finally {
    client.release();
  }
}

const worker = new Worker('job_application', processJob, { connection });

worker.on('completed', (job: Job) => {
  console.log(`Job ${job.id} has completed!`);
});

worker.on('failed', (job: Job | undefined, err: Error) => {
  console.log(`Job ${job?.id} has failed with ${err.message} `);
});

console.log('Browser worker started...');
