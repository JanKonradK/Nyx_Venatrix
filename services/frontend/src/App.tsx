import { motion } from 'framer-motion';
import { Activity, CheckCircle, Clock, Link as LinkIcon, Send, XCircle } from 'lucide-react';
import { FormEvent, useEffect, useState } from 'react';
import './index.css';

interface Job {
    id: string;
    original_url: string;
    title?: string;
    company_name?: string;
    status: 'queued' | 'in_progress' | 'applied' | 'failed' | 'skipped';
    created_at: string;
    cost_usd?: number;
}

function App() {
    const [url, setUrl] = useState('');
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchJobs = async () => {
        try {
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:3000'}/jobs`);
            const data = await res.json();
            setJobs(data.jobs || []);
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!url) return;
        setLoading(true);
        try {
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:3000'}/jobs/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, source: 'webapp' })
            });
            if (res.ok) {
                setUrl('');
                fetchJobs();
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'applied': return <CheckCircle size={16} />;
            case 'failed': return <XCircle size={16} />;
            case 'in_progress': return <Activity size={16} className="animate-pulse" />;
            default: return <Clock size={16} />;
        }
    };

    return (
        <div className="min-h-screen">
            <div className="container">
                <header className="mb-12 text-center">
                    <h1 className="text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-pink-500 animate-float">
                        Nyx Venatrix
                    </h1>
                    <p className="text-xl text-muted">Autonomous Job Application Agent</p>
                </header>

                {/* Analytics Section */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8"
                >
                    <div className="glass-panel p-4 text-center">
                        <h3 className="text-sm text-muted uppercase tracking-wider">Total Spent</h3>
                        <p className="text-2xl font-bold text-green-400">
                            ${jobs.reduce((acc, job) => acc + (Number(job.cost_usd) || 0), 0).toFixed(3)}
                        </p>
                    </div>
                    <div className="glass-panel p-4 text-center">
                        <h3 className="text-sm text-muted uppercase tracking-wider">Applications</h3>
                        <p className="text-2xl font-bold text-blue-400">
                            {jobs.filter(j => j.status === 'applied').length}
                        </p>
                    </div>
                    <div className="glass-panel p-4 text-center">
                        <h3 className="text-sm text-muted uppercase tracking-wider">Avg Cost/App</h3>
                        <p className="text-2xl font-bold text-purple-400">
                            ${(jobs.filter(j => j.status === 'applied').length > 0
                                ? jobs.reduce((acc, job) => acc + (Number(job.cost_usd) || 0), 0) / jobs.filter(j => j.status === 'applied').length
                                : 0).toFixed(3)}
                        </p>
                    </div>
                </motion.div>

                {/* Input Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-panel p-8 mb-12 max-w-2xl mx-auto"
                >
                    <form onSubmit={handleSubmit} className="flex gap-4">
                        <div className="relative flex-1">
                            <LinkIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 text-muted" size={20} />
                            <input
                                type="url"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                placeholder="Paste job URL (LinkedIn, Indeed, etc.)"
                                className="glass-input w-full pl-12"
                                required
                            />
                        </div>
                        <button type="submit" className="btn-primary flex items-center gap-2" disabled={loading}>
                            {loading ? <Activity className="animate-spin" /> : <Send size={20} />}
                            <span>Auto Apply</span>
                        </button>
                    </form>
                </motion.div>

                {/* Jobs Grid */}
                <div className="grid-jobs">
                    {jobs.map((job) => (
                        <motion.div
                            key={job.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="glass-panel p-6 hover:bg-white/5 transition-colors"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className={`status-badge status-${job.status} flex items-center gap-2`}>
                                    {getStatusIcon(job.status)}
                                    <span className="capitalize">{job.status.replace('_', ' ')}</span>
                                </div>
                                <span className="text-xs text-muted">{new Date(job.created_at).toLocaleDateString()}</span>
                            </div>
                            <h3 className="text-xl font-semibold mb-1">{job.title || 'Resolving...'}</h3>
                            <p className="text-muted mb-4">{job.company_name || job.original_url}</p>
                            <div className="flex justify-end">
                                <button className="text-sm text-primary hover:text-white transition-colors">
                                    View Details →
                                </button>
                            </div>
                        </motion.div>
                    ))}
                </div>

                {jobs.length === 0 && (
                    <div className="text-center text-muted mt-12">
                        <p>No jobs queued yet. Paste a URL to get started.</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default App;
