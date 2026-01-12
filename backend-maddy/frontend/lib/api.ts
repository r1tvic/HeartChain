/**
 * API Service for HeartChain Frontend (Decentralized / Stateless)
 */

// Backend API URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types
export type CampaignType = 'individual' | 'charity';
export type PriorityLevel = 'urgent' | 'normal';
export type CampaignStatus = 'active' | 'completed'; // Simplifed status

export type DocumentType =
    | 'medical_bill'
    | 'doctor_prescription'
    | 'hospital_letter'
    | 'id_proof'
    | 'ngo_certificate'
    | 'license'
    | 'trust_deed'
    | 'other';

export interface CampaignDocument {
    ipfs_hash: string;
    document_type: DocumentType;
    filename: string;
    mime_type: string;
    uploaded_at?: string;
}

export interface IndividualCampaignCreateRequest {
    title: string;
    description: string;
    target_amount: number;
    duration_days: number;
    category: string;
    priority?: PriorityLevel;
    image_url?: string;
    beneficiary_name: string;
    phone_number: string;
    residential_address: string;
    verification_notes?: string;
    documents?: CampaignDocument[];
}

export interface CharityCampaignCreateRequest {
    title: string;
    description: string;
    target_amount: number;
    duration_days: number;
    category: string;
    priority?: PriorityLevel;
    image_url?: string;
    organization_name: string;
    contact_person_name: string;
    contact_phone_number: string;
    official_address: string;
    verification_notes?: string;
    documents?: CampaignDocument[];
}

export interface CreateResponse {
    tx_hash: string;
    cid: string;
    status: string;
}

// Frontend Representation of a Campaign (Stored in LocalStorage for MVP)
export interface MockCampaign {
    id: string; // CID
    _id?: string; // Backwards compatibility
    cid: string;
    campaign_type: CampaignType;
    title: string;
    description: string;
    target_amount: number;
    raised_amount: number;
    duration_days: number;
    category: string;
    priority: PriorityLevel;
    status: CampaignStatus;
    image_url: string | null;
    organization_name?: string | null;
    created_at: string;
    end_date?: string; // Derived
    blockchain_tx_hash: string | null;
    on_chain_id?: string | null;
    documents_count?: number;
}

export type CampaignPublicResponse = MockCampaign;


class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultHeaders = { 'Content-Type': 'application/json' };

        const response = await fetch(url, {
            ...options,
            headers: { ...defaultHeaders, ...options.headers },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return response.json();
    }

    // Helper to save campaign to LocalStorage (Simulating Blockchain Indexer)
    private saveToLocalIndex(campaign: MockCampaign) {
        if (typeof window !== 'undefined') {
            const existing = JSON.parse(localStorage.getItem('heartchain_campaigns') || '[]');
            existing.unshift(campaign); // Add to top
            localStorage.setItem('heartchain_campaigns', JSON.stringify(existing));
        }
    }

    // ============== CREATE ==============

    async createIndividualCampaign(data: IndividualCampaignCreateRequest): Promise<CreateResponse> {
        const res = await this.request<CreateResponse>('/campaigns/individual', {
            method: 'POST',
            body: JSON.stringify(data),
        });

        // Save to mock storage so it appears in Browse
        this.saveToLocalIndex({
            id: res.cid,
            cid: res.cid,
            campaign_type: 'individual',
            title: data.title,
            description: data.description,
            target_amount: data.target_amount,
            raised_amount: 0,
            duration_days: data.duration_days,
            category: data.category,
            priority: data.priority || 'normal',
            status: 'active',
            image_url: data.image_url || null,
            created_at: new Date().toISOString(),
            blockchain_tx_hash: res.tx_hash
        });

        return res;
    }

    async createCharityCampaign(data: CharityCampaignCreateRequest): Promise<CreateResponse> {
        const res = await this.request<CreateResponse>('/campaigns/charity', {
            method: 'POST',
            body: JSON.stringify(data),
        });

        this.saveToLocalIndex({
            id: res.cid,
            cid: res.cid,
            campaign_type: 'charity',
            title: data.title,
            description: data.description,
            target_amount: data.target_amount,
            raised_amount: 0,
            duration_days: data.duration_days,
            category: data.category,
            priority: data.priority || 'normal',
            status: 'active',
            image_url: data.image_url || null,
            organization_name: data.organization_name,
            created_at: new Date().toISOString(),
            blockchain_tx_hash: res.tx_hash
        });

        return res;
    }

    // ============== BROWSE (MOCK FETCH) ==============

    async getCampaigns(params?: any): Promise<MockCampaign[]> {
        // Return from LocalStorage instead of Backend API (which is removed)
        if (typeof window !== 'undefined') {
            let campaigns: MockCampaign[] = JSON.parse(localStorage.getItem('heartchain_campaigns') || '[]');
            // Basic filtering logic
            if (params?.campaign_type) {
                campaigns = campaigns.filter(c => c.campaign_type === params.campaign_type);
            }
            if (params?.category) {
                campaigns = campaigns.filter(c => c.category === params.category);
            }
            return campaigns;
        }
        return [];
    }

    async getCampaign(id: string): Promise<MockCampaign | null> {
        if (typeof window !== 'undefined') {
            const campaigns: MockCampaign[] = JSON.parse(localStorage.getItem('heartchain_campaigns') || '[]');
            return campaigns.find(c => c.id === id) || null;
        }
        return null;
    }

    // ============== DOCUMENTS ==============

    async uploadDocument(file: File, documentType: DocumentType): Promise<CampaignDocument> {
        const formData = new FormData();
        formData.append('document', file); // changed key from 'file' to 'document' if backend expects?
        // Backend: document: UploadFile = File(...) -> field name 'document'
        // Wait, backend `routes/documents.py`: `async def upload_document(document: UploadFile = File(...), ...)`
        // Yes, field name is 'document'.

        formData.append('document_type', documentType);

        // Stateless endpoint: /documents/upload
        const response = await fetch(`${this.baseUrl}/documents/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        return response.json();
    }
}

export const api = new ApiClient(API_BASE_URL);
export { API_BASE_URL };


