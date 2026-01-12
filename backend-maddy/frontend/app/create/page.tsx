'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { api, CampaignType, IndividualCampaignCreateRequest, CharityCampaignCreateRequest, DocumentType } from '@/lib/api';

type Step = 1 | 2 | 3 | 4 | 5;

// Category options
const CATEGORIES = [
    'Medical',
    'Education',
    'Disaster Relief',
    'Community',
    'Environment',
    'Emergency',
    'Other'
];

// Document type labels
const INDIVIDUAL_DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
    { value: 'medical_bill', label: 'Medical Bill' },
    { value: 'doctor_prescription', label: 'Doctor Prescription' },
    { value: 'hospital_letter', label: 'Hospital Letter' },
    { value: 'id_proof', label: 'ID Proof' },
    { value: 'other', label: 'Other' },
];

const CHARITY_DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
    { value: 'ngo_certificate', label: 'NGO Registration Certificate' },
    { value: 'license', label: 'License' },
    { value: 'trust_deed', label: 'Trust Deed' },
    { value: 'other', label: 'Other' },
];

interface FormData {
    // Campaign type selection
    campaignType: CampaignType | '';

    // Step 1: Basic Info
    title: string;
    category: string;
    targetAmount: string;
    durationDays: string;

    // Step 2: Story
    description: string;
    imageUrl: string;

    // Step 3: Impact Plan (stored in description for now)
    impactPlan: string;

    // Individual-specific (Step 1)
    beneficiaryName: string;
    phoneNumber: string;
    residentialAddress: string;

    // Charity-specific (Step 1)
    organizationName: string;
    contactPersonName: string;
    contactPhoneNumber: string;
    officialAddress: string;

    // Documents
    documents: File[];
    documentTypes: DocumentType[];
}

const steps = [
    { number: 1, title: 'Basic Info' },
    { number: 2, title: 'Story & Media' },
    { number: 3, title: 'Impact Plan' },
    { number: 4, title: 'Documents' },
    { number: 5, title: 'Review' },
];

export default function CreateCampaignPage() {
    const router = useRouter();
    const [currentStep, setCurrentStep] = useState<Step>(1);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [createdCampaignId, setCreatedCampaignId] = useState<string | null>(null);

    const [formData, setFormData] = useState<FormData>({
        campaignType: '',
        title: '',
        category: '',
        targetAmount: '',
        durationDays: '90',
        description: '',
        imageUrl: '',
        impactPlan: '',
        beneficiaryName: '',
        phoneNumber: '',
        residentialAddress: '',
        organizationName: '',
        contactPersonName: '',
        contactPhoneNumber: '',
        officialAddress: '',
        documents: [],
        documentTypes: [],
    });

    const updateField = <K extends keyof FormData>(field: K, value: FormData[K]) => {
        setFormData((prev) => ({ ...prev, [field]: value }));
        setError(null);
    };

    const validateStep = (step: Step): boolean => {
        switch (step) {
            case 1:
                if (!formData.campaignType) {
                    setError('Please select a campaign type');
                    return false;
                }
                if (!formData.title.trim() || formData.title.length < 3) {
                    setError('Title must be at least 3 characters');
                    return false;
                }
                if (!formData.category) {
                    setError('Please select a category');
                    return false;
                }
                if (!formData.targetAmount || parseFloat(formData.targetAmount) <= 0) {
                    setError('Please enter a valid target amount');
                    return false;
                }
                if (formData.campaignType === 'individual') {
                    if (!formData.beneficiaryName.trim()) {
                        setError('Beneficiary name is required');
                        return false;
                    }
                    if (!formData.phoneNumber.trim() || formData.phoneNumber.length < 10 || formData.phoneNumber.length > 20) {
                        setError('Phone number must be between 10 and 20 characters');
                        return false;
                    }
                    if (!formData.residentialAddress.trim() || formData.residentialAddress.length < 5) {
                        setError('Residential address must be at least 5 characters');
                        return false;
                    }
                } else {
                    if (!formData.organizationName.trim()) {
                        setError('Organization name is required');
                        return false;
                    }
                    if (!formData.contactPersonName.trim()) {
                        setError('Contact person name is required');
                        return false;
                    }
                    if (!formData.contactPhoneNumber.trim() || formData.contactPhoneNumber.length < 10 || formData.contactPhoneNumber.length > 20) {
                        setError('Phone number must be between 10 and 20 characters');
                        return false;
                    }
                    if (!formData.officialAddress.trim() || formData.officialAddress.length < 5) {
                        setError('Official address must be at least 5 characters');
                        return false;
                    }
                }
                return true;
            case 2:
                if (!formData.description.trim() || formData.description.length < 10) {
                    setError('Description must be at least 10 characters');
                    return false;
                }
                return true;
            case 3:
                return true; // Impact plan is optional
            case 4:
                return true; // Documents can be uploaded later
            default:
                return true;
        }
    };

    const nextStep = () => {
        if (validateStep(currentStep)) {
            if (currentStep < 5) setCurrentStep((prev) => (prev + 1) as Step);
        }
    };

    const prevStep = () => {
        if (currentStep > 1) setCurrentStep((prev) => (prev - 1) as Step);
        setError(null);
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        setError(null);

        try {
            // 1. Upload documents first to get CIDs
            const uploadedDocs = [];
            for (let i = 0; i < formData.documents.length; i++) {
                const file = formData.documents[i];
                const docType = formData.documentTypes[i] || 'other';
                try {
                    const docRes = await api.uploadDocument(file, docType);
                    uploadedDocs.push(docRes);
                } catch (err) {
                    console.error('Document upload failed:', err);
                    // Fail fast? Or continue? Let's fail fast for safety.
                    throw new Error(`Failed to upload document: ${file.name}`);
                }
            }

            // Combine description with impact plan
            const fullDescription = formData.impactPlan
                ? `${formData.description}\n\n---\n\n**How Funds Will Be Used:**\n${formData.impactPlan}`
                : formData.description;

            let response;

            if (formData.campaignType === 'individual') {
                const payload: IndividualCampaignCreateRequest = {
                    title: formData.title,
                    description: fullDescription,
                    target_amount: parseFloat(formData.targetAmount),
                    duration_days: parseInt(formData.durationDays),
                    category: formData.category,
                    priority: 'normal',
                    image_url: formData.imageUrl || undefined,
                    beneficiary_name: formData.beneficiaryName,
                    phone_number: formData.phoneNumber,
                    residential_address: formData.residentialAddress,
                    documents: uploadedDocs
                };
                response = await api.createIndividualCampaign(payload);
            } else {
                const payload: CharityCampaignCreateRequest = {
                    title: formData.title,
                    description: fullDescription,
                    target_amount: parseFloat(formData.targetAmount),
                    duration_days: parseInt(formData.durationDays),
                    category: formData.category,
                    priority: 'normal',
                    image_url: formData.imageUrl || undefined,
                    organization_name: formData.organizationName,
                    contact_person_name: formData.contactPersonName,
                    contact_phone_number: formData.contactPhoneNumber,
                    official_address: formData.officialAddress,
                    documents: uploadedDocs
                };
                response = await api.createCharityCampaign(payload);
            }

            setCreatedCampaignId(response.cid);

            // Redirect to success or browse page
            // Using logic from api.ts, the campaign is now in local storage with ID = CID.
            router.push(`/campaigns/${response.cid}?created=true&tx=${response.tx_hash}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create campaign');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files) {
            const fileArray = Array.from(files);
            const docTypes = fileArray.map(() => 'other' as DocumentType);
            updateField('documents', [...formData.documents, ...fileArray]);
            updateField('documentTypes', [...formData.documentTypes, ...docTypes]);
        }
    };

    const removeDocument = (index: number) => {
        const newDocs = [...formData.documents];
        const newTypes = [...formData.documentTypes];
        newDocs.splice(index, 1);
        newTypes.splice(index, 1);
        updateField('documents', newDocs);
        updateField('documentTypes', newTypes);
    };

    const updateDocumentType = (index: number, type: DocumentType) => {
        const newTypes = [...formData.documentTypes];
        newTypes[index] = type;
        updateField('documentTypes', newTypes);
    };

    const documentTypeOptions = formData.campaignType === 'individual'
        ? INDIVIDUAL_DOCUMENT_TYPES
        : CHARITY_DOCUMENT_TYPES;

    const renderStep = () => {
        switch (currentStep) {
            case 1:
                return (
                    <div className="space-y-6">
                        {/* Campaign Type Selection */}
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-3">
                                Campaign Type *
                            </label>
                            <div className="grid grid-cols-2 gap-4">
                                <button
                                    type="button"
                                    onClick={() => updateField('campaignType', 'individual')}
                                    className={`p-6 rounded-xl border-2 text-left transition-all ${formData.campaignType === 'individual'
                                        ? 'border-[var(--accent)] bg-[var(--accent)]/5'
                                        : 'border-[var(--beige-300)] hover:border-[var(--beige-400)]'
                                        }`}
                                >
                                    <div className="text-2xl mb-2">👤</div>
                                    <p className="font-bold text-[var(--text-primary)]">Individual</p>
                                    <p className="text-sm text-[var(--text-secondary)]">Personal emergencies, medical needs</p>
                                </button>
                                <button
                                    type="button"
                                    onClick={() => updateField('campaignType', 'charity')}
                                    className={`p-6 rounded-xl border-2 text-left transition-all ${formData.campaignType === 'charity'
                                        ? 'border-[var(--accent)] bg-[var(--accent)]/5'
                                        : 'border-[var(--beige-300)] hover:border-[var(--beige-400)]'
                                        }`}
                                >
                                    <div className="text-2xl mb-2">🏢</div>
                                    <p className="font-bold text-[var(--text-primary)]">Charity / NGO</p>
                                    <p className="text-sm text-[var(--text-secondary)]">Registered organizations</p>
                                </button>
                            </div>
                        </div>

                        {formData.campaignType && (
                            <>
                                {/* Basic Fields */}
                                <div>
                                    <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                        Campaign Title *
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.title}
                                        onChange={(e) => updateField('title', e.target.value)}
                                        placeholder="Give your campaign a compelling title"
                                        className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                        Category *
                                    </label>
                                    <select
                                        value={formData.category}
                                        onChange={(e) => updateField('category', e.target.value)}
                                        className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none bg-white"
                                    >
                                        <option value="">Select a category</option>
                                        {CATEGORIES.map((cat) => (
                                            <option key={cat} value={cat}>{cat}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                            Target Amount ($) *
                                        </label>
                                        <input
                                            type="number"
                                            value={formData.targetAmount}
                                            onChange={(e) => updateField('targetAmount', e.target.value)}
                                            placeholder="0"
                                            min="1"
                                            className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                            Duration (Days) *
                                        </label>
                                        <input
                                            type="number"
                                            value={formData.durationDays}
                                            onChange={(e) => updateField('durationDays', e.target.value)}
                                            placeholder="90"
                                            min="1"
                                            max="365"
                                            className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none"
                                        />
                                    </div>
                                </div>

                                {/* Individual-specific fields */}
                                {formData.campaignType === 'individual' && (
                                    <>
                                        <div className="pt-4 border-t border-[var(--beige-200)]">
                                            <h3 className="font-bold text-[var(--text-primary)] mb-4">Beneficiary Information</h3>
                                            <p className="text-sm text-[var(--text-secondary)] mb-4">
                                                🔒 This information is encrypted and only visible to admins for verification.
                                            </p>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                                Beneficiary Full Name *
                                            </label>
                                            <input
                                                type="text"
                                                value={formData.beneficiaryName}
                                                onChange={(e) => updateField('beneficiaryName', e.target.value)}
                                                placeholder="Full legal name"
                                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                                Phone Number *
                                            </label>
                                            <input
                                                type="tel"
                                                value={formData.phoneNumber}
                                                onChange={(e) => updateField('phoneNumber', e.target.value)}
                                                placeholder="10-digit phone number"
                                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                                Residential Address *
                                            </label>
                                            <textarea
                                                value={formData.residentialAddress}
                                                onChange={(e) => updateField('residentialAddress', e.target.value)}
                                                placeholder="Full address"
                                                rows={3}
                                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none resize-none"
                                            />
                                        </div>
                                    </>
                                )}

                                {/* Charity-specific fields */}
                                {formData.campaignType === 'charity' && (
                                    <>
                                        <div className="pt-4 border-t border-[var(--beige-200)]">
                                            <h3 className="font-bold text-[var(--text-primary)] mb-4">Organization Information</h3>
                                            <p className="text-sm text-[var(--text-secondary)] mb-4">
                                                🔒 Contact details are encrypted. Organization name is public.
                                            </p>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                                Organization Name * (Public)
                                            </label>
                                            <input
                                                type="text"
                                                value={formData.organizationName}
                                                onChange={(e) => updateField('organizationName', e.target.value)}
                                                placeholder="Registered organization name"
                                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                                Contact Person Name *
                                            </label>
                                            <input
                                                type="text"
                                                value={formData.contactPersonName}
                                                onChange={(e) => updateField('contactPersonName', e.target.value)}
                                                placeholder="Full name"
                                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                                Contact Phone Number *
                                            </label>
                                            <input
                                                type="tel"
                                                value={formData.contactPhoneNumber}
                                                onChange={(e) => updateField('contactPhoneNumber', e.target.value)}
                                                placeholder="10-digit phone number"
                                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                                Official/Registered Address *
                                            </label>
                                            <textarea
                                                value={formData.officialAddress}
                                                onChange={(e) => updateField('officialAddress', e.target.value)}
                                                placeholder="Registered office address"
                                                rows={3}
                                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none resize-none"
                                            />
                                        </div>
                                    </>
                                )}
                            </>
                        )}
                    </div>
                );

            case 2:
                return (
                    <div className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                Campaign Story *
                            </label>
                            <textarea
                                value={formData.description}
                                onChange={(e) => updateField('description', e.target.value)}
                                placeholder="Tell your story. Why are you raising funds? What will the money be used for? Be specific and heartfelt."
                                rows={10}
                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none resize-none"
                            />
                            <p className="text-sm text-[var(--text-secondary)] mt-2">
                                {formData.description.length}/5000 characters
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                Campaign Image URL (Optional)
                            </label>
                            <input
                                type="url"
                                value={formData.imageUrl}
                                onChange={(e) => updateField('imageUrl', e.target.value)}
                                placeholder="https://example.com/image.jpg"
                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none"
                            />
                            <p className="text-sm text-[var(--text-secondary)] mt-2">
                                Provide a URL to your campaign banner image
                            </p>
                        </div>
                    </div>
                );

            case 3:
                return (
                    <div className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                Impact Plan
                            </label>
                            <p className="text-sm text-[var(--text-secondary)] mb-4">
                                Explain how the funds will be used. Break down the costs to build trust with donors.
                            </p>
                            <textarea
                                value={formData.impactPlan}
                                onChange={(e) => updateField('impactPlan', e.target.value)}
                                placeholder={`Example:\n- $5,000 - Medical supplies and equipment\n- $3,000 - Hospital fees\n- $2,000 - Recovery and rehabilitation`}
                                rows={10}
                                className="w-full px-4 py-3 border-2 border-[var(--beige-300)] rounded-xl focus:border-[var(--accent)] focus:outline-none resize-none font-mono text-sm"
                            />
                        </div>

                        <div className="bg-[var(--beige-100)] rounded-xl p-4">
                            <p className="text-sm text-[var(--text-secondary)]">
                                💡 <strong>Tip:</strong> Campaigns with detailed fund breakdowns receive 40% more donations on average.
                            </p>
                        </div>
                    </div>
                );

            case 4:
                return (
                    <div className="space-y-6">
                        <div className="bg-[var(--beige-100)] rounded-xl p-6">
                            <h3 className="font-bold text-[var(--text-primary)] mb-2">Supporting Documents</h3>
                            <p className="text-sm text-[var(--text-secondary)]">
                                Upload documents to verify your campaign. All files are encrypted before storage for security.
                            </p>
                        </div>

                        {/* File Upload */}
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                                Upload Documents
                            </label>
                            <input
                                type="file"
                                onChange={handleFileChange}
                                multiple
                                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                                className="hidden"
                                id="document-upload"
                            />
                            <label
                                htmlFor="document-upload"
                                className="block border-2 border-dashed border-[var(--beige-400)] rounded-xl p-8 text-center hover:border-[var(--accent)] transition-colors cursor-pointer"
                            >
                                <div className="text-4xl mb-2">📄</div>
                                <p className="text-[var(--text-primary)] font-medium">Click to upload documents</p>
                                <p className="text-sm text-[var(--text-secondary)]">PDF, JPG, PNG, DOC (Max 10MB each)</p>
                            </label>
                        </div>

                        {/* Uploaded Files List */}
                        {formData.documents.length > 0 && (
                            <div className="space-y-3">
                                <h4 className="font-medium text-[var(--text-primary)]">Uploaded Files</h4>
                                {formData.documents.map((file, index) => (
                                    <div key={index} className="flex items-center gap-4 p-4 bg-white border border-[var(--beige-300)] rounded-xl">
                                        <div className="text-2xl">📎</div>
                                        <div className="flex-1">
                                            <p className="font-medium text-[var(--text-primary)]">{file.name}</p>
                                            <p className="text-xs text-[var(--text-secondary)]">{(file.size / 1024).toFixed(1)} KB</p>
                                        </div>
                                        <select
                                            value={formData.documentTypes[index]}
                                            onChange={(e) => updateDocumentType(index, e.target.value as DocumentType)}
                                            className="px-3 py-2 border border-[var(--beige-300)] rounded-lg text-sm"
                                        >
                                            {documentTypeOptions.map((opt) => (
                                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                                            ))}
                                        </select>
                                        <button
                                            onClick={() => removeDocument(index)}
                                            className="p-2 text-[var(--urgent)] hover:bg-[var(--urgent)]/10 rounded-lg"
                                        >
                                            ✕
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                );

            case 5:
                return (
                    <div className="space-y-6">
                        <div className="text-center mb-8">
                            <div className="text-5xl mb-4">🎉</div>
                            <h2 className="text-2xl font-bold text-[var(--text-primary)]">Review Your Campaign</h2>
                            <p className="text-[var(--text-secondary)]">Make sure everything looks good before submitting.</p>
                        </div>

                        <div className="bg-[var(--beige-100)] rounded-xl p-6 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-sm text-[var(--text-secondary)]">Campaign Type</p>
                                    <p className="font-bold text-[var(--text-primary)] capitalize">{formData.campaignType}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-[var(--text-secondary)]">Category</p>
                                    <p className="font-medium text-[var(--text-primary)]">{formData.category}</p>
                                </div>
                            </div>
                            <div>
                                <p className="text-sm text-[var(--text-secondary)]">Title</p>
                                <p className="font-bold text-[var(--text-primary)]">{formData.title}</p>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-sm text-[var(--text-secondary)]">Target Amount</p>
                                    <p className="font-bold text-[var(--accent)]">
                                        ${parseFloat(formData.targetAmount || '0').toLocaleString()}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-sm text-[var(--text-secondary)]">Duration</p>
                                    <p className="font-medium text-[var(--text-primary)]">{formData.durationDays} days</p>
                                </div>
                            </div>
                            <div>
                                <p className="text-sm text-[var(--text-secondary)]">Story Preview</p>
                                <p className="text-[var(--text-primary)] line-clamp-3">{formData.description}</p>
                            </div>
                            <div>
                                <p className="text-sm text-[var(--text-secondary)]">Documents</p>
                                <p className="font-medium text-[var(--text-primary)]">{formData.documents.length} file(s) uploaded</p>
                            </div>
                        </div>

                        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4">
                            <span className="text-xl">⚠️</span>
                            <div>
                                <p className="font-medium text-amber-800">Before you submit</p>
                                <p className="text-sm text-amber-700">
                                    Your campaign will be saved as DRAFT. You can submit it for verification from the campaign page.
                                    Sensitive information (names, phone numbers, addresses) will be encrypted before storage.
                                </p>
                            </div>
                        </div>
                    </div>
                );
        }
    };

    return (
        <div className="min-h-screen bg-[var(--beige-100)] py-12">
            <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Header */}
                <motion.div
                    className="text-center mb-12"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <h1 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)] mb-4">
                        Start a Campaign
                    </h1>
                    <p className="text-[var(--text-secondary)]">
                        Create a campaign to raise funds for a cause you care about.
                    </p>
                </motion.div>

                {/* Progress Steps */}
                <div className="mb-12">
                    <div className="flex items-center justify-between">
                        {steps.map((step, index) => (
                            <div key={step.number} className="flex items-center">
                                <div className="flex flex-col items-center">
                                    <div
                                        className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-colors ${currentStep >= step.number
                                            ? 'bg-[var(--accent)] text-white'
                                            : 'bg-[var(--beige-300)] text-[var(--text-secondary)]'
                                            }`}
                                    >
                                        {currentStep > step.number ? '✓' : step.number}
                                    </div>
                                    <p className="text-xs text-[var(--text-secondary)] mt-2 hidden md:block">
                                        {step.title}
                                    </p>
                                </div>
                                {index < steps.length - 1 && (
                                    <div
                                        className={`flex-1 h-1 mx-2 rounded-full transition-colors ${currentStep > step.number
                                            ? 'bg-[var(--accent)]'
                                            : 'bg-[var(--beige-300)]'
                                            }`}
                                    />
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Error Message */}
                {error && (
                    <motion.div
                        className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700"
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        {error}
                    </motion.div>
                )}

                {/* Form Card */}
                <motion.div
                    key={currentStep}
                    className="bg-white rounded-2xl p-8 shadow-soft border border-[var(--card-border)]"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                >
                    <h2 className="text-xl font-bold text-[var(--text-primary)] mb-6">
                        {steps[currentStep - 1].title}
                    </h2>

                    {renderStep()}

                    {/* Navigation Buttons */}
                    <div className="flex items-center justify-between mt-8 pt-6 border-t border-[var(--beige-200)]">
                        <button
                            onClick={prevStep}
                            disabled={currentStep === 1}
                            className="px-6 py-3 text-[var(--text-secondary)] font-medium hover:text-[var(--text-primary)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            ← Back
                        </button>

                        {currentStep < 5 ? (
                            <button
                                onClick={nextStep}
                                className="px-8 py-3 bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] text-white font-bold rounded-xl hover:opacity-90 transition-opacity"
                            >
                                Continue →
                            </button>
                        ) : (
                            <button
                                onClick={handleSubmit}
                                disabled={isSubmitting}
                                className="px-8 py-3 bg-gradient-to-r from-[var(--success)] to-[#7BA828] text-white font-bold rounded-xl hover:opacity-90 transition-opacity disabled:opacity-70 flex items-center gap-2"
                            >
                                {isSubmitting ? (
                                    <>
                                        <motion.div
                                            className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                        />
                                        Creating...
                                    </>
                                ) : (
                                    '🚀 Create Campaign'
                                )}
                            </button>
                        )}
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
