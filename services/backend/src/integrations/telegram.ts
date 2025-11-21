/**
 * Telegram bot integration - embedded in backend
 */

import { Telegraf } from 'telegraf';
import { JobService } from '../domain/job';

export class TelegramBot {
    private bot: Telegraf;
    private jobService: JobService;

    constructor(jobService: JobService) {
        const token = process.env.TELEGRAM_BOT_TOKEN;
        if (!token) {
            console.warn('⚠️  TELEGRAM_BOT_TOKEN not set. Telegram bot disabled.');
            this.bot = null as any;
            return;
        }

        this.bot = new Telegraf(token);
        this.jobService = jobService;
        this.setupHandlers();
    }

    private setupHandlers() {
        if (!this.bot) return;

        this.bot.start((ctx) => {
            ctx.reply(
                'Welcome to DeepApply! 🤖\n\n' +
                'Send me a job URL and I\'ll automatically apply for you.\n\n' +
                'Commands:\n' +
                '/start - Show this message\n' +
                '/status - Check bot status'
            );
        });

        this.bot.command('status', async (ctx) => {
            ctx.reply('✅ Bot is active and ready to process job applications!');
        });

        // Handle URLs
        this.bot.on('text', async (ctx) => {
            const text = ctx.message.text;

            // Simple URL detection
            if (text.includes('http://') || text.includes('https://')) {
                try {
                    const result = await this.jobService.createAndQueue({
                        url: text,
                        source: 'telegram'
                    });

                    ctx.reply(
                        `✅ Job queued successfully!\n\n` +
                        `Job ID: ${result.job_id}\n` +
                        `Status: ${result.status}\n\n` +
                        `I'll process this application and notify you when it's done.`
                    );
                } catch (error: any) {
                    ctx.reply(`❌ Error: ${error.message}`);
                }
            } else {
                ctx.reply(
                    'Please send me a valid job URL.\n' +
                    'Example: https://example.com/jobs/123'
                );
            }
        });
    }

    async launch() {
        if (!this.bot) {
            console.log('Telegram bot not configured (missing TELEGRAM_BOT_TOKEN)');
            return;
        }

        await this.bot.launch();
        console.log('✅ Telegram bot started');
    }

    async stop() {
        if (!this.bot) return;
        this.bot.stop('SIGINT');
    }
}
