import axios from 'axios';
import dotenv from 'dotenv';
import { Telegraf } from 'telegraf';

dotenv.config();

const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN || '');
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:3000';

bot.start((ctx) => {
    ctx.reply('Welcome to DeepApply! Send me a job URL to get started.');
});

bot.on('text', async (ctx) => {
    const text = ctx.message.text;

    // Simple URL extraction regex
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const urls = text.match(urlRegex);

    if (!urls || urls.length === 0) {
        return ctx.reply('I didn\'t find any URLs in your message.');
    }

    for (const url of urls) {
        try {
            ctx.reply(`Processing URL: ${url}...`);

            const response = await axios.post(`${BACKEND_URL}/jobs/apply`, {
                url: url,
                source: 'telegram',
                notes: `Forwarded from Telegram user ${ctx.from.username || ctx.from.id}`
            });

            const { jobId, status } = response.data;
            ctx.reply(`✅ Job queued!\nID: ${jobId}\nStatus: ${status}`);
        } catch (error: any) {
            console.error('Error sending job to backend:', error.message);
            ctx.reply(`❌ Failed to queue job: ${url}\nError: ${error.message}`);
        }
    }
});

bot.launch().then(() => {
    console.log('Telegram bot started');
}).catch((err) => {
    console.error('Failed to start bot', err);
});

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
