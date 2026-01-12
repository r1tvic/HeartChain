'use client';

import { useState, useEffect, use } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import HeartProgressBar from '@/components/HeartProgressBar';
import DonationModal from '@/components/DonationModal';
import PriorityBanner from '@/components/PriorityBanner';
import { api, CampaignPublicResponse } from '@/lib/api';
import { getCampaignById, categoryLabels, categoryColors, Campaign } from '@/data/mockData';
import { formatCurrency, calculatePercentage, formatDate, truncateHash, getDaysRemainingText } from '@/lib/utils';

interface PageProps {
    params: Promise<{ id: string }>;
}

// Convert API response to frontend Campaign format
function apiToFrontendCampaign(apiCampaign: CampaignPublicResponse): Campaign {
    const endDate = apiCampaign.end_date
        ? new Date(apiCampaign.end_date)
        : new Date(new Date(apiCampaign.created_at).getTime() + apiCampaign.duration_days * 86400000);

    const daysLeft = Math.max(0, Math.ceil(
        (endDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    ));

    // Map API category to frontend category
    const categoryMap: Record<string, Campaign['category']> = {
        'medical': 'medical',
        'education': 'education',
        'disaster relief': 'disaster',
        'community': 'community',
        'environment': 'environment',
        'emergency': 'emergency',
    };

    const category = categoryMap[apiCampaign.category?.toLowerCase()] || 'community';

    return {
        id: apiCampaign.id,
        title: apiCampaign.title,
        description: apiCampaign.description.split('\n')[0], // First paragraph as short description
        fullDescription: apiCampaign.description,
        category,
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
        impactBreakdown: [
            { label: 'Campaign Goal', percentage: 100, amount: apiCampaign.target_amount },
        ],
        recentDonors: [],
    };
}

export default function CampaignDetailPage({ params }: PageProps) {
    const { id } = use(params);
    const searchParams = useSearchParams();
    const justCreated = searchParams.get('created') === 'true';

    const [campaign, setCampaign] = useState<Campaign | null>(null);
    const [apiCampaign, setApiCampaign] = useState<CampaignPublicResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isDonationModalOpen, setIsDonationModalOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<'story' | 'updates' | 'donors'>('story');

    useEffect(() => {
        async function fetchCampaign() {
            setIsLoading(true);
            setError(null);

            try {
                // Try to fetch from backend first
                const response = await api.getCampaign(id);
                if (!response) throw new Error('Campaign not found');

                setApiCampaign(response);
                setCampaign(apiToFrontendCampaign(response));
            } catch (err) {
                console.error('Failed to fetch from backend:', err);
                // Fall back to mock data
                const mockCampaign = getCampaignById(id);
                if (mockCampaign) {
                    setCampaign(mockCampaign);
                } else {
                    setError('Campaign not found');
                }
            } finally {
                setIsLoading(false);
            }
        }

        fetchCampaign();
    }, [id]);

    if (isLoading) {
        return (
            <div className="min-h-screen bg-[var(--beige-100)] flex items-center justify-center">
                <motion.div
                    className="text-center"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                >
                    <div className="w-16 h-16 border-4 border-[var(--accent)] border-t-transparent rounded-full mx-auto mb-4 animate-spin" />
                    <p className="text-[var(--text-secondary)]">Loading campaign...</p>
                </motion.div>
            </div>
        );
    }

    if (error || !campaign) {
        return (
            <div className="min-h-screen bg-[var(--beige-100)] flex items-center justify-center">
                <div className="text-center">
                    <div className="text-6xl mb-4">😔</div>
                    <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Campaign Not Found</h1>
                    <p className="text-[var(--text-secondary)] mb-6">{error || 'This campaign does not exist.'}</p>
                    <Link
                        href="/campaigns"
                        className="px-6 py-3 bg-[var(--accent)] text-white font-medium rounded-xl hover:opacity-90"
                    >
                        Browse Campaigns
                    </Link>
                </div>
            </div>
        );
    }

    const percentage = calculatePercentage(campaign.raised, campaign.goal);
    const categoryColor = categoryColors[campaign.category] || '#8B4513';

    return (
        <div className="min-h-screen bg-[var(--beige-100)]">
            {/* Success Banner for Just Created */}
            {justCreated && (
                <motion.div
                    className="bg-[var(--success)] text-white py-3 px-4 text-center"
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    ✅ Campaign created successfully! It&apos;s saved as a draft. Submit it for verification when ready.
                </motion.div>
            )}

            {/* Priority Banner */}
            {campaign.isHighPriority && (
                <PriorityBanner daysLeft={campaign.daysLeft} />
            )}

            {/* Hero Section */}
            <section className="relative bg-gradient-to-b from-[var(--beige-200)] to-[var(--beige-100)] py-8">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    {/* Breadcrumb */}
                    <nav className="mb-6">
                        <ol className="flex items-center gap-2 text-sm">
                            <li>
                                <Link href="/" className="text-[var(--text-secondary)] hover:text-[var(--accent)]">Home</Link>
                            </li>
                            <li className="text-[var(--text-secondary)]">/</li>
                            <li>
                                <Link href="/campaigns" className="text-[var(--text-secondary)] hover:text-[var(--accent)]">Campaigns</Link>
                            </li>
                            <li className="text-[var(--text-secondary)]">/</li>
                            <li className="text-[var(--text-primary)] font-medium truncate max-w-[200px]">{campaign.title}</li>
                        </ol>
                    </nav>

                    <div className="grid lg:grid-cols-2 gap-12 items-start">
                        {/* Left Column - Image & Info */}
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                        >
                            {/* Campaign Image */}
                            <div className="relative rounded-2xl overflow-hidden shadow-soft-lg mb-6">
                                <div
                                    className="w-full h-64 md:h-80 bg-gradient-to-br from-[var(--beige-300)] to-[var(--beige-400)]"
                                    style={{
                                        backgroundImage: `url(${campaign.image})`,
                                        backgroundSize: 'cover',
                                        backgroundPosition: 'center',
                                    }}
                                />
                                {/* Category Badge */}
                                <div
                                    className="absolute top-4 left-4 px-4 py-1.5 rounded-full text-white text-sm font-medium"
                                    style={{ backgroundColor: categoryColor }}
                                >
                                    {categoryLabels[campaign.category]}
                                </div>
                                {/* Status Badge */}
                                {apiCampaign && (
                                    <div className={`absolute top-4 right-4 px-3 py-1.5 rounded-full text-sm font-medium ${apiCampaign.status === 'active' ? 'bg-[var(--success)] text-white' :
                                            apiCampaign.status === 'completed' ? 'bg-blue-500 text-white' :
                                                'bg-gray-500 text-white'
                                        }`}>
                                        {apiCampaign.status.toUpperCase()}
                                    </div>
                                )}
                            </div>

                            {/* Campaign Title & Creator */}
                            <h1 className="text-2xl md:text-3xl font-bold text-[var(--text-primary)] mb-4">
                                {campaign.title}
                            </h1>

                            <div className="flex items-center gap-3 mb-6">
                                <div className="w-10 h-10 rounded-full bg-[var(--beige-300)] flex items-center justify-center text-lg">
                                    👤
                                </div>
                                <div>
                                    <p className="font-medium text-[var(--text-primary)]">{campaign.creatorName}</p>
                                    <p className="text-sm text-[var(--text-secondary)]">Campaign Organizer</p>
                                </div>
                            </div>

                            {/* Quick Stats */}
                            <div className="grid grid-cols-3 gap-4 mb-6">
                                <div className="bg-white rounded-xl p-4 text-center shadow-soft">
                                    <p className="text-2xl font-bold text-[var(--accent)]">{campaign.contributors.toLocaleString()}</p>
                                    <p className="text-xs text-[var(--text-secondary)]">Donors</p>
                                </div>
                                <div className="bg-white rounded-xl p-4 text-center shadow-soft">
                                    <p className={`text-2xl font-bold ${campaign.daysLeft <= 7 ? 'text-[var(--urgent)]' : 'text-[var(--text-primary)]'}`}>
                                        {campaign.daysLeft}
                                    </p>
                                    <p className="text-xs text-[var(--text-secondary)]">Days Left</p>
                                </div>
                                <div className="bg-white rounded-xl p-4 text-center shadow-soft">
                                    <p className="text-2xl font-bold text-[var(--success)]">{percentage}%</p>
                                    <p className="text-xs text-[var(--text-secondary)]">Funded</p>
                                </div>
                            </div>
                        </motion.div>

                        {/* Right Column - Heart & Donation */}
                        <motion.div
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.2 }}
                            className="lg:sticky lg:top-24"
                        >
                            <div className="bg-white rounded-2xl p-8 shadow-soft-lg border border-[var(--card-border)]">
                                {/* Large Animated Heart */}
                                <div className="flex justify-center mb-8">
                                    <HeartProgressBar percentage={percentage} size="lg" animated={true} />
                                </div>

                                {/* Progress Info */}
                                <div className="text-center mb-6">
                                    <p className="text-4xl font-bold text-[var(--accent)] mb-2">
                                        {formatCurrency(campaign.raised)}
                                    </p>
                                    <p className="text-[var(--text-secondary)]">
                                        raised of <span className="font-medium text-[var(--text-primary)]">{formatCurrency(campaign.goal)}</span> goal
                                    </p>
                                </div>

                                {/* Progress Bar */}
                                <div className="mb-6">
                                    <div className="h-3 bg-[var(--beige-200)] rounded-full overflow-hidden">
                                        <motion.div
                                            className="h-full bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] rounded-full"
                                            initial={{ width: 0 }}
                                            animate={{ width: `${percentage}%` }}
                                            transition={{ duration: 1.5, ease: 'easeOut' }}
                                        />
                                    </div>
                                </div>

                                {/* Time Remaining */}
                                <div className="flex items-center justify-center gap-2 mb-8 text-[var(--text-secondary)]">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <span className={campaign.daysLeft <= 7 ? 'text-[var(--urgent)] font-medium' : ''}>
                                        {getDaysRemainingText(campaign.daysLeft)}
                                    </span>
                                </div>

                                {/* Blockchain Info */}
                                {apiCampaign?.on_chain_id === null && (
                                    <div className="bg-[var(--beige-100)] rounded-xl p-3 mb-6 text-center">
                                        <p className="text-xs text-[var(--text-secondary)]">
                                            🔗 Blockchain integration coming soon
                                        </p>
                                    </div>
                                )}

                                {/* Donate Button - Hidden for now as per requirements */}
                                <div className="bg-[var(--beige-100)] rounded-xl p-4 text-center">
                                    <p className="text-sm text-[var(--text-secondary)]">
                                        💝 Donation feature will be enabled after blockchain integration
                                    </p>
                                </div>

                                {/* Share Buttons */}
                                <div className="mt-6 pt-6 border-t border-[var(--beige-200)]">
                                    <p className="text-sm text-[var(--text-secondary)] text-center mb-3">Share this campaign</p>
                                    <div className="flex justify-center gap-3">
                                        <button className="w-10 h-10 flex items-center justify-center bg-[var(--beige-100)] rounded-full hover:bg-[var(--accent)] hover:text-white transition-all">
                                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                                            </svg>
                                        </button>
                                        <button className="w-10 h-10 flex items-center justify-center bg-[var(--beige-100)] rounded-full hover:bg-[#1877F2] hover:text-white transition-all">
                                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                                            </svg>
                                        </button>
                                        <button className="w-10 h-10 flex items-center justify-center bg-[var(--beige-100)] rounded-full hover:bg-[#0A66C2] hover:text-white transition-all">
                                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                </div>
            </section>

            {/* Content Tabs Section */}
            <section className="py-12">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid lg:grid-cols-3 gap-8">
                        {/* Main Content */}
                        <div className="lg:col-span-2">
                            {/* Tab Navigation */}
                            <div className="flex gap-1 mb-8 bg-[var(--beige-200)] p-1 rounded-xl">
                                {(['story', 'updates', 'donors'] as const).map((tab) => (
                                    <button
                                        key={tab}
                                        onClick={() => setActiveTab(tab)}
                                        className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all capitalize ${activeTab === tab
                                            ? 'bg-white text-[var(--accent)] shadow-soft'
                                            : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                                            }`}
                                    >
                                        {tab}
                                    </button>
                                ))}
                            </div>

                            {/* Tab Content */}
                            <motion.div
                                key={activeTab}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="bg-white rounded-2xl p-8 shadow-soft border border-[var(--card-border)]"
                            >
                                {activeTab === 'story' && (
                                    <div className="prose max-w-none">
                                        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6">Campaign Story</h2>
                                        {campaign.fullDescription.split('\n\n').map((paragraph, index) => (
                                            <p key={index} className="text-[var(--text-secondary)] mb-4 leading-relaxed whitespace-pre-wrap">
                                                {paragraph}
                                            </p>
                                        ))}
                                    </div>
                                )}

                                {activeTab === 'updates' && (
                                    <div>
                                        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6">Campaign Updates</h2>
                                        {campaign.updates.length > 0 ? (
                                            <div className="space-y-6">
                                                {campaign.updates.map((update) => (
                                                    <div key={update.id} className="border-l-4 border-[var(--accent)] pl-4">
                                                        <p className="text-sm text-[var(--text-secondary)] mb-1">{formatDate(update.date)}</p>
                                                        <h3 className="font-bold text-[var(--text-primary)] mb-2">{update.title}</h3>
                                                        <p className="text-[var(--text-secondary)]">{update.content}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <p className="text-[var(--text-secondary)]">No updates yet. Check back soon!</p>
                                        )}
                                    </div>
                                )}

                                {activeTab === 'donors' && (
                                    <div>
                                        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6">Recent Donors</h2>
                                        {campaign.recentDonors.length > 0 ? (
                                            <div className="space-y-4">
                                                {campaign.recentDonors.map((donor) => (
                                                    <div key={donor.id} className="flex items-center justify-between py-3 border-b border-[var(--beige-200)] last:border-0">
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-10 h-10 rounded-full bg-[var(--beige-200)] flex items-center justify-center">
                                                                💝
                                                            </div>
                                                            <div>
                                                                <p className="font-medium text-[var(--text-primary)]">{donor.name}</p>
                                                                <p className="text-xs text-[var(--text-secondary)]">{formatDate(donor.date)}</p>
                                                            </div>
                                                        </div>
                                                        <div className="text-right">
                                                            <p className="font-bold text-[var(--accent)]">{formatCurrency(donor.amount)}</p>
                                                            <p className="text-xs text-[var(--text-secondary)] font-mono">
                                                                {truncateHash(donor.transactionHash)}
                                                            </p>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <p className="text-[var(--text-secondary)]">No donations yet. Be the first to donate!</p>
                                        )}
                                    </div>
                                )}
                            </motion.div>
                        </div>

                        {/* Sidebar */}
                        <div className="space-y-6">
                            {/* Campaign Info */}
                            <div className="bg-white rounded-2xl p-6 shadow-soft border border-[var(--card-border)]">
                                <h3 className="font-bold text-[var(--text-primary)] mb-4">Campaign Details</h3>
                                <div className="space-y-3 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-secondary)]">Created</span>
                                        <span className="font-medium text-[var(--text-primary)]">{formatDate(campaign.createdAt)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-secondary)]">Category</span>
                                        <span className="font-medium text-[var(--text-primary)]">{categoryLabels[campaign.category]}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-secondary)]">Duration</span>
                                        <span className="font-medium text-[var(--text-primary)]">{campaign.daysLeft + 30} days</span>
                                    </div>
                                    {apiCampaign && (
                                        <div className="flex justify-between">
                                            <span className="text-[var(--text-secondary)]">Documents</span>
                                            <span className="font-medium text-[var(--text-primary)]">{apiCampaign.documents_count || 0} file(s)</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Blockchain Proof */}
                            <div className="bg-white rounded-2xl p-6 shadow-soft border border-[var(--card-border)]">
                                <h3 className="font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                                    <svg className="w-5 h-5 text-[var(--success)]" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                    </svg>
                                    Blockchain Status
                                </h3>
                                <div className="bg-[var(--beige-100)] rounded-xl p-4">
                                    <p className="text-xs text-[var(--text-secondary)] mb-1">On-Chain ID</p>
                                    <p className="text-sm font-mono text-[var(--text-primary)]">
                                        {apiCampaign?.on_chain_id || 'Not yet on blockchain'}
                                    </p>
                                </div>
                                <p className="text-xs text-[var(--text-secondary)] mt-3">
                                    Smart contract integration will be added in the next phase.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Donation Modal */}
            <DonationModal
                isOpen={isDonationModalOpen}
                onClose={() => setIsDonationModalOpen(false)}
                campaignTitle={campaign.title}
                currentAmount={campaign.raised}
                goalAmount={campaign.goal}
            />
        </div>
    );
}
