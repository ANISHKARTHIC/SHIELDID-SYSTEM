import { create } from 'zustand'

export interface CustomerProfile {
  id: string
  name: string
  dob: string
  age: number
  documentType: 'uk_driving_licence' | 'passport' | 'other'
  documentNumber: string
  expiryDate: string
  issueDate: string
  address: string
  nationality: string
  blacklistStatus: 'none' | 'temporary' | 'permanent'
  blacklistReason?: string
  blacklistExpiry?: string
  membership: 'VIP' | 'Regular' | 'Guest List' | 'Staff' | 'None'
  visitCount: number
  incidentsCount: number
  photoUrl: string
  idScanUrl?: string
  notes?: string
  vipTier?: string
  managerNotes?: string
  warnings?: number
}

export interface VerificationLog {
  id: string
  timestamp: string
  customerName: string
  documentType: string
  age: number
  riskScore: number
  recommendation: 'PASS' | 'CHECK' | 'DENY'
  staffDecision: 'PASS' | 'DENY' | 'CHECK' | 'NONE'
  staffMember: string
  ocrConfidence: number
  qualityScore: number
  authenticityScore: number
}

interface AppState {
  activeTab: 'dashboard' | 'visitors' | 'blacklist' | 'incidents' | 'settings' | 'history' | 'notifications' | 'users' | 'venues' | 'occupancy'
  setActiveTab: (tab: 'dashboard' | 'visitors' | 'blacklist' | 'incidents' | 'settings' | 'history' | 'notifications' | 'users' | 'venues' | 'occupancy') => void
  
  customers: CustomerProfile[]
  addCustomer: (customer: CustomerProfile) => void
  updateCustomer: (id: string, updates: Partial<CustomerProfile>) => void
  
  logs: VerificationLog[]
  addLog: (log: VerificationLog) => void
  
  incidents: {
    id: string
    customerId: string
    customerName: string
    type: 'violence' | 'fake_id' | 'property_damage' | 'drug_related' | 'other'
    description: string
    date: string
    staffNotes?: string
  }[]
  addIncident: (incident: any) => void
  
  currentScan: {
    sessionId: string | null
    step: 'idle' | 'capturing_id' | 'processing_id' | 'capturing_face' | 'processing_face' | 'decision' | 'complete'
    idImageFile: File | null
    faceImageFile: File | null
    classification: any | null
    ocr: any | null
    validation: any | null
    venueCheck: any | null
    aiDecision: string | null
    error: string | null
  }
  setCurrentScan: (scan: Partial<AppState['currentScan']>) => void
  resetScan: () => void
  setCustomers: (customers: CustomerProfile[]) => void
  setLogs: (logs: VerificationLog[]) => void
  setIncidents: (incidents: any[]) => void
  resetStore: () => void
}

export const useAppStore = create<AppState>((set) => ({
  activeTab: 'dashboard',
  setActiveTab: (tab) => set({ activeTab: tab }),

  // Real data is loaded from the backend on mount (see page.tsx); these
  // start empty rather than seeded with fixture people, since a permanently
  // stale mock would otherwise linger for any field the API never refreshes.
  customers: [],
  addCustomer: (customer) => set((state) => ({ customers: [customer, ...state.customers] })),
  updateCustomer: (id, updates) => set((state) => ({
    customers: state.customers.map(c => c.id === id ? { ...c, ...updates } : c)
  })),

  logs: [],
  addLog: (log) => set((state) => ({ logs: [log, ...state.logs] })),

  incidents: [],
  addIncident: (incident) => set((state) => ({ incidents: [incident, ...state.incidents] })),
  
  currentScan: {
    sessionId: null,
    step: 'idle',
    idImageFile: null,
    faceImageFile: null,
    classification: null,
    ocr: null,
    validation: null,
    venueCheck: null,
    aiDecision: null,
    error: null,
  },
  setCurrentScan: (scan) => set((state) => ({
    currentScan: { ...state.currentScan, ...scan }
  })),
  resetScan: () => set({
    currentScan: {
      sessionId: null,
      step: 'idle',
      idImageFile: null,
      faceImageFile: null,
      classification: null,
      ocr: null,
      validation: null,
      venueCheck: null,
      aiDecision: null,
      error: null,
    }
  }),
  setCustomers: (customers) => set((state) => {
    // Each poll re-signs photoUrl/idScanUrl with a fresh S3 signature even
    // when the underlying photo hasn't changed, which would otherwise swap
    // every <img> src on every refresh and make the browser re-fetch/
    // flicker the image. Keep the previously-rendered URL whenever the
    // object key itself (the path, ignoring the presign query string) is
    // the same, so the <img> only actually changes when the photo does.
    const previousByKey = new Map(state.customers.map((c) => [c.id, c]));
    const samePhotoTarget = (a: string, b: string) => {
      if (!a || !b) return a === b;
      const path = (url: string) => url.split('?')[0];
      return path(a) === path(b);
    };
    const merged = customers.map((incoming) => {
      const previous = previousByKey.get(incoming.id);
      if (!previous) return incoming;
      return {
        ...incoming,
        photoUrl: samePhotoTarget(previous.photoUrl, incoming.photoUrl) ? previous.photoUrl : incoming.photoUrl,
        idScanUrl:
          previous.idScanUrl && incoming.idScanUrl && samePhotoTarget(previous.idScanUrl, incoming.idScanUrl)
            ? previous.idScanUrl
            : incoming.idScanUrl,
      };
    });
    return { customers: merged };
  }),
  setLogs: (logs) => set({ logs }),
  setIncidents: (incidents) => set({ incidents }),

  // Zustand state is a module-level singleton that outlives any one login
  // session — without this, logging out and a different-role user logging
  // back in on the same tab could leave a stale activeTab the new role
  // can't see (blank content pane) and stale visitor/log/incident data
  // from the previous account.
  resetStore: () => set({
    activeTab: 'dashboard',
    customers: [],
    logs: [],
    incidents: [],
    currentScan: {
      sessionId: null,
      step: 'idle',
      idImageFile: null,
      faceImageFile: null,
      classification: null,
      ocr: null,
      validation: null,
      venueCheck: null,
      aiDecision: null,
      error: null,
    },
  }),
}))
