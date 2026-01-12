'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CampaignCard from '@/components/CampaignCard';
import { api, CampaignPublicResponse, CampaignType as ApiCampaignType } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Campaign, categoryLabels } from '@/data/mockData';

type SortOption = 'newest' | 'ending' | 'funded' | 'priority';
type CategoryFilter = string | 'all';

const sortOptions: { value: SortOption; label: string }[] = [
    { value: 'newest', label: 'Newest First' },
    { value: 'ending', label: 'Ending Soon' },
    { value: 'funded', label: 'Most Funded' },
    { value: 'priority', label: 'High Priority' },
];

// Convert API response to frontend Campaign format
function apiToFrontendCampaign(apiCampaign: CampaignPublicResponse): Campaign {
    const endDate = apiCampaign.end_date
        ? new Date(apiCampaign.end_date)
        : new Date(new Date(apiCampaign.created_at).getTime() + apiCampaign.duration_days * 86400000);

    const daysLeft = Math.max(0, Math.ceil(
        (endDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    ));

    return {
        id: apiCampaign.id,
        title: apiCampaign.title,
        description: apiCampaign.description,
        fullDescription: apiCampaign.description,
        category: (apiCampaign.category?.toLowerCase().replace(' ', '_') || 'community') as Campaign['category'],
        image: apiCampaign.image_url || '/campaigns/default.jpg',
        goal: apiCampaign.target_amount,
        raised: apiCampaign.raised_amount,
        daysLeft,
        contributors: Math.floor(apiCampaign.raised_amount / 50), // Estimate
        creatorName: apiCampaign.organization_name || 'Campaign Creator',
        creatorAvatar: '/avatars/default.jpg',
        isVerified: apiCampaign.status === 'active',
        isHighPriority: apiCampaign.priority === 'urgent',
        createdAt: apiCampaign.created_at,
        updates: [],
        impactBreakdown: [],
        recentDonors: [],
    };
}

export default function CampaignsPage() {
    const [searchQuery, setSearchQuery] = useState('');
    const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all');
    const [sortBy, setSortBy] = useState<SortOption>('priority');
    const [priorityOnly, setPriorityOnly] = useState(false);
    const [showFilters, setShowFilters] = useState(false);

    // API state
    const [campaigns, setCampaigns] = useState<Campaign[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [useBackend, setUseBackend] = useState(true);

    // Fetch campaigns from backend
    useEffect(() => {
        async function fetchCampaigns() {
            setIsLoading(true);
            setError(null);

            try {
                const response = await api.getCampaigns({ limit: 100 });
                const frontendCampaigns = response.map(apiToFrontendCampaign);
                setCampaigns(frontendCampaigns);
                setUseBackend(true);
            } catch (err) {
                console.error('Failed to fetch from backend:', err);
                setError('Using demo data (backend not connected)');
                // Fall back to mock data
                const { mockCampaigns } = await import('@/data/mockData');
                setCampaigns(mockCampaigns);
                setUseBackend(false);
            } finally {
                setIsLoading(false);
            }
        }

        fetchCampaigns();
    }, []);

    const filteredCampaigns = useMemo(() => {
        let result = [...campaigns];

        // Search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            result = result.filter(
                (c) =>
                    c.title.toLowerCase().includes(query) ||
                    c.description.toLowerCase().includes(query)
            );
        }

        // Category filter
        if (categoryFilter !== 'all') {
            result = result.filter((c) => c.category === categoryFilter);
        }

        // Priority filter
        if (priorityOnly) {
            result = result.filter((c) => c.isHighPriority);
        }

        // Sorting
        switch (sortBy) {
            case 'newest':
                result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
                break;
            case 'ending':
                result.sort((a, b) => a.daysLeft - b.daysLeft);
                break;
            case 'funded':
                result.sort((a, b) => b.raised - a.raised);
                break;
            case 'priority':
                result.sort((a, b) => {
                    if (a.isHighPriority !== b.isHighPriority) return a.isHighPriority ? -1 : 1;
                    return a.daysLeft - b.daysLeft;
                });
                break;
        }

        return result;
    }, [campaigns, searchQuery, categoryFilter, sortBy, priorityOnly]);

    const stats = useMemo(() => {
        const total = campaigns.reduce((sum, c) => sum + c.raised, 0);
        const urgent = campaigns.filter((c) => c.isHighPriority).length;
        return { total, urgent, count: campaigns.length };
    }, [campaigns]);

    if (isLoading) {
        return (
            <div className="min-h-screen bg-[var(--beige-100)] flex items-center justify-center">
                <motion.div
                    className="text-center"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                >
                    <div className="w-16 h-16 border-4 border-[var(--accent)] border-t-transparent rounded-full mx-auto mb-4 animate-spin" />
                    <p className="text-[var(--text-secondary)]">Loading campaigns...</p>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[var(--beige-100)]">
            {/* Header Section */}
            <section className="bg-gradient-to-b from-[var(--beige-200)] to-[var(--beige-100)] py-12">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-center mb-8"
                    >
                        <h1 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)] mb-4">
                            Browse Campaigns
                        </h1>
                        <p className="text-[var(--text-secondary)] max-w-2xl mx-auto">
                            Discover causes that matter and make a real difference in people&apos;s lives.
                        </p>
                        {error && (
                            <p className="text-sm text-amber-600 mt-2 bg-amber-50 inline-block px-4 py-1 rounded-full">
                                ⚠️ {error}
                            </p>
                        )}
                        {useBackend && !error && (
                            <p className="text-sm text-[var(--success)] mt-2">
                                ✓ Connected to backend
                            </p>
                        )}
                    </motion.div>

                    {/* Stats Bar */}
                    <motion.div
                        className="flex flex-wrap justify-center gap-6 mb-8"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                    >
                        <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl shadow-soft">
                            <span className="text-lg">📊</span>
                            <span className="text-sm text-[var(--text-secondary)]">
                                <span className="font-bold text-[var(--text-primary)]">{stats.count}</span> Campaigns
                            </span>
                        </div>
                        <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl shadow-soft">
                            <span className="text-lg">💰</span>
                            <span className="text-sm text-[var(--text-secondary)]">
                                <span className="font-bold text-[var(--accent)]">{formatCurrency(stats.total)}</span> Raised
                            </span>
                        </div>
                        <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl shadow-soft">
                            <span className="text-lg">🔥</span>
                            <span className="text-sm text-[var(--text-secondary)]">
                                <span className="font-bold text-[var(--urgent)]">{stats.urgent}</span> Urgent
                            </span>
                        </div>
                    </motion.div>

                    {/* Search Bar */}
                    <motion.div
                        className="max-w-2xl mx-auto"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                        <div className="relative">
                            <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-secondary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <input
                                type="text"
                                placeholder="Search campaigns..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-12 pr-4 py-4 bg-white border-2 border-[var(--beige-300)] rounded-2xl focus:border-[var(--accent)] focus:outline-none text-[var(--text-primary)] shadow-soft"
                            />
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* Main Content */}
            <section className="py-8">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="lg:flex lg:gap-8">
                        {/* Sidebar Filters - Desktop */}
                        <motion.aside
                            className="hidden lg:block w-64 flex-shrink-0"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                        >
                            <div className="sticky top-24 space-y-6">
                                {/* Categories */}
                                <div className="bg-white rounded-2xl p-6 shadow-soft border border-[var(--card-border)]">
                                    <h3 className="font-bold text-[var(--text-primary)] mb-4">Categories</h3>
                                    <div className="space-y-2">
                                        <button
                                            onClick={() => setCategoryFilter('all')}
                                            className={`w-full text-left px-4 py-2 rounded-xl transition-colors ${categoryFilter === 'all'
                                                ? 'bg-[var(--accent)] text-white'
                                                : 'hover:bg-[var(--beige-200)] text-[var(--text-secondary)]'
                                                }`}
                                        >
                                            All Categories
                                        </button>
                                        {(Object.keys(categoryLabels) as Campaign['category'][]).map((cat) => (
                                            <button
                                                key={cat}
                                                onClick={() => setCategoryFilter(cat)}
                                                className={`w-full text-left px-4 py-2 rounded-xl transition-colors ${categoryFilter === cat
                                                    ? 'bg-[var(--accent)] text-white'
                                                    : 'hover:bg-[var(--beige-200)] text-[var(--text-secondary)]'
                                                    }`}
                                            >
                                                {categoryLabels[cat]}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Priority Filter */}
                                <div className="bg-white rounded-2xl p-6 shadow-soft border border-[var(--card-border)]">
                                    <h3 className="font-bold text-[var(--text-primary)] mb-4">Priority</h3>
                                    <label className="flex items-center gap-3 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={priorityOnly}
                                            onChange={(e) => setPriorityOnly(e.target.checked)}
                                            className="w-5 h-5 rounded border-[var(--beige-400)] text-[var(--accent)] focus:ring-[var(--accent)]"
                                        />
                                        <span className="text-[var(--text-secondary)]">High Priority Only</span>
                                    </label>
                                </div>

                                {/* Sort */}
                                <div className="bg-white rounded-2xl p-6 shadow-soft border border-[var(--card-border)]">
                                    <h3 className="font-bold text-[var(--text-primary)] mb-4">Sort By</h3>
                                    <div className="space-y-2">
                                        {sortOptions.map((option) => (
                                            <button
                                                key={option.value}
                                                onClick={() => setSortBy(option.value)}
                                                className={`w-full text-left px-4 py-2 rounded-xl transition-colors ${sortBy === option.value
                                                    ? 'bg-[var(--accent)] text-white'
                                                    : 'hover:bg-[var(--beige-200)] text-[var(--text-secondary)]'
                                                    }`}
                                            >
                                                {option.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </motion.aside>

                        {/* Mobile Filter Toggle */}
                        <div className="lg:hidden mb-4">
                            <button
                                onClick={() => setShowFilters(!showFilters)}
                                className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl shadow-soft border border-[var(--card-border)]"
                            >
                                <svg className="w-5 h-5 text-[var(--text-secondary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                                </svg>
                                <span className="font-medium text-[var(--text-primary)]">Filters</span>
                            </button>
                        </div>

                        {/* Mobile Filters Panel */}
                        <AnimatePresence>
                            {showFilters && (
                                <motion.div
                                    className="lg:hidden fixed inset-0 z-50 bg-black/50"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    onClick={() => setShowFilters(false)}
                                >
                                    <motion.div
                                        className="absolute right-0 top-0 bottom-0 w-80 bg-white p-6 overflow-y-auto"
                                        initial={{ x: '100%' }}
                                        animate={{ x: 0 }}
                                        exit={{ x: '100%' }}
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        <div className="flex items-center justify-between mb-6">
                                            <h2 className="text-xl font-bold text-[var(--text-primary)]">Filters</h2>
                                            <button
                                                onClick={() => setShowFilters(false)}
                                                className="p-2 hover:bg-[var(--beige-200)] rounded-lg"
                                            >
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                </svg>
                                            </button>
                                        </div>

                                        <div className="space-y-6">
                                            <div>
                                                <h3 className="font-bold text-[var(--text-primary)] mb-3">Categories</h3>
                                                <div className="space-y-2">
                                                    <button
                                                        onClick={() => { setCategoryFilter('all'); setShowFilters(false); }}
                                                        className={`w-full text-left px-4 py-2 rounded-xl ${categoryFilter === 'all' ? 'bg-[var(--accent)] text-white' : 'bg-[var(--beige-100)]'
                                                            }`}
                                                    >
                                                        All Categories
                                                    </button>
                                                    {(Object.keys(categoryLabels) as Campaign['category'][]).map((cat) => (
                                                        <button
                                                            key={cat}
                                                            onClick={() => { setCategoryFilter(cat); setShowFilters(false); }}
                                                            className={`w-full text-left px-4 py-2 rounded-xl ${categoryFilter === cat ? 'bg-[var(--accent)] text-white' : 'bg-[var(--beige-100)]'
                                                                }`}
                                                        >
                                                            {categoryLabels[cat]}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>

                                            <div>
                                                <h3 className="font-bold text-[var(--text-primary)] mb-3">Sort By</h3>
                                                <div className="space-y-2">
                                                    {sortOptions.map((option) => (
                                                        <button
                                                            key={option.value}
                                                            onClick={() => { setSortBy(option.value); setShowFilters(false); }}
                                                            className={`w-full text-left px-4 py-2 rounded-xl ${sortBy === option.value ? 'bg-[var(--accent)] text-white' : 'bg-[var(--beige-100)]'
                                                                }`}
                                                        >
                                                            {option.label}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Campaign Grid */}
                        <div className="flex-1">
                            {/* Results Header */}
                            <div className="flex items-center justify-between mb-6">
                                <p className="text-[var(--text-secondary)]">
                                    Showing <span className="font-bold text-[var(--text-primary)]">{filteredCampaigns.length}</span> campaigns
                                </p>
                            </div>

                            {/* Grid */}
                            {filteredCampaigns.length > 0 ? (
                                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">
                                    {filteredCampaigns.map((campaign, index) => (
                                        <CampaignCard key={campaign.id} campaign={campaign} index={index} />
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-16">
                                    <div className="text-6xl mb-4">🔍</div>
                                    <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">No campaigns found</h3>
                                    <p className="text-[var(--text-secondary)]">Try adjusting your filters or search query</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}
