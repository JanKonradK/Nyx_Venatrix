import axios from 'axios';
import { Job, Worker } from 'bullmq';
import dotenv from 'dotenv';
import { Pool } from 'pg';
import { chromium } from 'playwright-extra';
import stealth from 'puppeteer-extra-plugin-stealth';
import { extractFormSchema, fillForm } from './automation/form';

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
    const content = await page.content(); // In real app, use better scraping (e.g. Readability)
    const bodyText = await page.evaluate(() => document.body.innerText);

    console.log(`Scraped title: ${title}`);

    // Extract Form Schema
    console.log('Extracting form schema...');
    const schema = await extractFormSchema(page);
    console.log(`Found ${schema.fields.length} fields.`);

    let answers = {};
    if (schema.fields.length > 0) {
      // Generate Answers via Backend API
      console.log('Requesting answers from backend...');
      try {
        const response = await axios.post(`${process.env.BACKEND_URL || 'http://backend:3000'}/jobs/generate-answers`, {
          jobDescription: bodyText.substring(0, 5000), // Truncate for safety
          formFields: schema.fields
        });
        answers = response.data.answers;
        console.log('Received answers:', JSON.stringify(answers, null, 2));

        // Fill Form
        console.log('Filling form...');
        await fillForm(page, schema, answers);

        // Take screenshot after filling
        await page.screenshot({ path: `/app/screenshots/${jobId}_filled.png` }).catch(() => { });

        // Submit (Optional - be careful with auto-submit in dev)
        // await submitForm(page, schema);
      } catch (error) {
        console.error('Failed to generate answers or fill form:', error);
      }
    }

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
