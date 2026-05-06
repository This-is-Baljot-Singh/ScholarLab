/**
 * # ScholarLab Student Dashboard Implementation
 * 
 * Production-grade React/Vite SPA components for student profile and daily workflow showcase.
 * This document describes the architecture, components, and integration patterns.
 * 
 * ## Overview
 * 
 * The Student Dashboard provides a comprehensive view of:
 * - **Live Sessions**: Today's active and upcoming lectures
 * - **Zero-Trust Attendance**: Multi-step verification with biometric and geolocation
 * - **Curriculum Resources**: Dynamically unlocked materials after successful check-in
 * - **Performance Analytics**: Real-time radar chart showing attendance, engagement, and safety
 * 
 * ## Architecture
 * 
 * ### Technology Stack
 * - **Framework**: React 19 with TypeScript
 * - **Build**: Vite 8+
 * - **Styling**: Tailwind CSS 4
 * - **State Management**: Zustand
 * - **Data Fetching**: React Query (TanStack Query)
 * - **Charts**: Recharts
 * - **Authentication**: WebAuthn (SimpleWebAuthn)
 * - **UI Components**: Custom Tailwind-based components
 * 
 * ### Folder Structure
 * 
 * ```
 * frontend/src/
 * ├── api/
 * │   ├── client.ts (Axios instance with auth interceptors)
 * │   └── studentAPI.ts ★ NEW: Attendance & curriculum APIs
 * ├── features/
 * │   ├── attendance/
 * │   │   ├── components/
 * │   │   │   ├── LiveSessionsWidget.tsx ★ NEW: Session display
 * │   │   │   ├── MarkAttendanceFlow.tsx (existing: 6-gate flow)
 * │   │   │   └── index.ts
 * │   │   └── pages/
 * │   │       ├── StudentDashboardPage.tsx ★ ENHANCED: Error boundaries
 * │   │       └── index.ts
 * │   ├── curriculum/
 * │   │   ├── components/
 * │   │   │   ├── CurriculumGrid.tsx (existing)
 * │   │   │   ├── StudentCurriculumView.tsx ★ NEW: Timeline view
 * │   │   │   └── index.ts
 * │   │   └── pages/
 * │   └── analytics/
 * │       ├── components/
 * │       │   ├── StudentPerformanceRadar.tsx ★ NEW: Recharts radar
 * │       │   └── index.ts
 * │       └── pages/
 * ├── shared/
 * │   ├── components/
 * │   │   └── ErrorBoundary.tsx ★ NEW: Error handling
 * │   ├── ui/
 * │   │   ├── Button.tsx
 * │   │   ├── SkeletonLoader.tsx
 * │   │   └── BottomSheet.tsx
 * │   └── hooks/
 * │       └── useStudentWebSocket.ts
 * ├── store/
 * │   ├── authStore.ts (existing)
 * │   └── dashboardStore.ts ★ NEW: Attendance flow state
 * ├── types/
 * │   ├── student.ts (existing)
 * │   └── dashboard.ts ★ NEW: Dashboard types
 * └── config/
 *     └── queryClient.ts
 * ```
 * 
 * ## Core Components
 * 
 * ### 1. StudentDashboardPage (Main Container)
 * 
 * **Location**: `features/attendance/pages/StudentDashboardPage.tsx`
 * **Responsibility**: Main page orchestrator with error boundaries
 * 
 * **Features**:
 * - Wraps all sections with error boundaries
 * - Manages attendance modal state
 * - Fetches dashboard data and recent unlocks
 * - Integrates WebSocket for real-time sync
 * - Invalidates queries on successful check-in
 * 
 * **Key Sections**:
 * 1. Overview: Welcome, risk score, next session
 * 2. Upcoming sessions: 3-column grid layout
 * 3. Performance radar: Real-time metrics visualization
 * 4. Curriculum resources: Dynamic unlock animation
 * 5. Attendance modal: Multi-step verification flow
 * 
 * ### 2. LiveSessionsWidget
 * 
 * **Location**: `features/attendance/components/LiveSessionsWidget.tsx`\n * **Props**:
 * - `onSelectSession?`: Callback when session selected\n * **API Integration**:
 * - Endpoint: `GET /api/attendance/sessions`
 * - Fallback: Mock data if API fails
 * - Query key: `['attendance', 'sessions']`
 * - Stale time: 2 minutes\n * **Features**:
 * - Live session indicator with pulse animation
 * - Location and time display
 * - Status badges (Ongoing/Upcoming/Completed)
 * - Graceful fallback with warning badge
 * - Mark Attendance button integration\n * **Error Handling**:
 * - Automatic fallback to `MOCK_SESSIONS`
 * - Amber warning badge shows mock state
 * - Retry on API recovery\n * **Component Hierarchy**:
 * ```
 * LiveSessionsWidget
 * ├── Header with status badge
 * ├── SessionCard (repeated)
 * │   ├── Title + Instructor
 * │   ├── Time (Clock icon)
 * │   ├── Location (MapPin icon)
 * │   ├── Class code
 * │   └── Mark Attendance button
 * └── Empty state if no sessions
 * ```\n * ### 3. MarkAttendanceFlow (Existing Enhancement)
 * 
 * **Location**: `features/attendance/components/MarkAttendanceFlow.tsx`
 * **Status**: Already production-ready\n * **Three-Step Process**:
 * 1. **Location**: Requests high-accuracy geolocation via Geolocation API
 *    - Validates within geofence radius
 *    - Shows accuracy meter
 * 2. **Biometric**: Triggers WebAuthn authentication
 *    - Device verification
 *    - Privacy-preserving liveness check
 *    - Mocks if hardware key unavailable
 * 3. **Success**: Displays 6 security gates
 *    - Geofence ✓
 *    - Cryptographic ✓
 *    - Multimodal ✓
 *    - Nonce ✓
 *    - Biometric ✓
 *    - Device ✓\n * **Integration Points**:
 * - Uses `useStudentDashboardStore` for state management
 * - Calls POST `/api/attendance/checkin`
 * - Triggers `setShouldRefreshResources` on success
 * - Auto-closes after 3 seconds on success\n * ### 4. StudentCurriculumView
 * 
 * **Location**: `features/curriculum/components/StudentCurriculumView.tsx`
 * **Props**:
 * - `sessionId: string`: Fetch resources for this session
 * - `showAllUnlocked?: boolean`: Show all vs session-specific (default: false)\n * **API Integration**:
 * - Endpoint: `GET /api/curriculum/resources/{sessionId}`
 * - Fallback (all): `GET /api/curriculum/unlocked`
 * - Query invalidation on successful check-in
 * - Auto-refetch via `shouldRefreshResources` flag\n * **Features**:
 * - Separates recently unlocked (< 5 min) from older
 * - Slide-in animation for new items
 * - Green highlight for recently unlocked
 * - Resource type icons (PDF, Slides, Video, Quiz, Assignment)
 * - Metadata display (duration, pages, points)
 * - Download button with external link\n * **Resource Card States**:
 * ```
 * Recently Unlocked:
 * ├── Green border highlight
 * ├── Slide-in animation
 * ├── "New" badge
 * ├── Gradient hover effect
 * └── Full action buttons\n * Other Resources:
 * ├── Subtle styling
 * ├── Fade-in style
 * └── Hover elevation\n * ### 5. StudentPerformanceRadar
 * 
 * **Location**: `features/analytics/components/StudentPerformanceRadar.tsx`
 * **Props**:
 * - `mockMode?: boolean`: Use mock data (default: false)\n * **API Integration**:
 * - Endpoint: `GET /api/analytics/performance`
 * - Returns: attendance rate, engagement, risk score
 * - Query key: `['analytics', 'performance']`
 * - Stale time: 5 minutes\n * **Visualization**:
 * - Recharts radar chart with 3 axes:
 *   1. **Attendance Rate**: 0-100%
 *   2. **Curriculum Engagement**: 0-100%
 *   3. **Safety Score**: 0-100 (inverted risk)\n * **Status Indicators**:
 * - **Safe** (≥80): Green badge + green styling
 * - **Moderate** (50-79): Amber badge + amber styling
 * - **At-Risk** (<50): Red badge + red styling\n * **Mock Data**:
 * ```javascript
 * {
 *   attendanceRate: 95,
 *   curriculumEngagement: 88,
 *   riskScore: 92, // 92 = safe
 *   lastUpdated: new Date().toISOString()
 * }
 * ```\n * **Metric Cards**:
 * - 3-column grid below chart
 * - Emoji icons
 * - Percentage display with color coding\n * ### 6. ErrorBoundary
 * 
 * **Location**: `shared/components/ErrorBoundary.tsx`
 * **Components**:
 * - `<ErrorBoundary>`: Class component wrapper
 * - `<AsyncErrorBoundary>`: React Query integration
 * - `withErrorBoundary()`: HOC for wrapping
 * - `useApiErrorHandler()`: Hook for manual error handling\n * **Features**:
 * - Automatic error logging
 * - Retry functionality
 * - Graceful fallback UI
 * - Doesn't stop entire app (unlike unhandled errors)\n * **Usage Patterns**:
 * ```tsx
 * // Wrapper pattern
 * <ErrorBoundary>\n *   <Section />\n * </ErrorBoundary>\n * \n * // React Query pattern\n * <AsyncErrorBoundary isError={error} error={error} onRetry={refetch}>\n *   <Component />\n * </AsyncErrorBoundary>\n * \n * // HOC pattern\n * const SafeComponent = withErrorBoundary(Component);\n * ```\n * ## State Management\n * \n * ### Zustand Store (dashboardStore.ts)\n * 
 * ```typescript\n * interface StudentDashboardStore {
 *   // Attendance flow
 *   attendanceFlow: AttendanceFlowState
 *   setAttendanceFlow: (state) => void
n *   updateAttendanceFlow: (partial) => void
 *   resetAttendanceFlow: () => void\n *   // Session
 *   selectedSessionId: string | null
 *   setSelectedSessionId: (id) => void\n *   // UI
 *   isMarkingAttendance: boolean
 *   setIsMarkingAttendance: (is) => void
 *   showAttendanceModal: boolean
 *   setShowAttendanceModal: (show) => void\n *   // Cache
 *   shouldRefreshResources: boolean
 *   setShouldRefreshResources: (should) => void
 * }
 * ```\n * ## Data Flow
 * 
 * ### Attendance Check-in → Curriculum Unlock
 * 
 * ```
 * User opens StudentDashboardPage
n * ↓
 * Renders LiveSessionsWidget
 * ├─ Fetches GET /api/attendance/sessions
 * └─ Falls back to mock if error\n * ↓
 * User clicks "Mark Attendance"
 * ├─ Opens MarkAttendanceFlow modal
 * └─ Sets selectedSessionId in store\n * ↓
 * Step 1: Location
 * ├─ Calls attendanceAPI.requestNonce()
 * └─ Gets { nonce, sessionId, expiresAt }\n * ↓
 * Step 2: Biometric
 * ├─ Triggers WebAuthn authentication
 * └─ Mocks if hardware unavailable\n * ↓
 * Step 3: Submit Check-in
 * ├─ POST /api/attendance/checkin
 * └─ Receives { checkInId, status, gates: {...} }\n * ↓
 * Success State
 * ├─ Show success animation + 6 gates
 * ├─ Call setShouldRefreshResources(true)
 * └─ Emit onSuccess callback\n * ↓
 * StudentCurriculumView notices flag
 * ├─ Invalidates query cache
 * └─ Re-fetches GET /api/curriculum/resources/{sessionId}\n * ↓
 * New Resources Appear
 * ├─ Slide-in animation
 * ├─ Green highlight
 * └─ Recently unlocked section\n * ```\n * ## API Contracts
 * 
 * ### GET /api/attendance/sessions
 * \n * **Response**:
 * ```typescript\n * AttendanceSession[] = [\n *   {\n *     id: string\n *     lectureId: string\n *     title: string\n *     instructor: string\n *     startTime: ISO8601\n *     endTime: ISO8601\n *     location: string\n *     classCode: string\n *     status: 'upcoming' | 'ongoing' | 'completed'\n *     geofenceLatitude: number\n *     geofenceLongitude: number\n *     geofenceRadius: number // in meters\n *   }\n * ]\n * ```\n * \n * ### POST /api/attendance/sessions/{sessionId}/nonce\n * \n * **Response**:
 * ```typescript\n * {\n *   nonce: string // cryptographically random\n *   expiresAt: ISO8601\n *   sessionId: string\n * }\n * ```\n * \n * ### POST /api/attendance/checkin
 * \n * **Request**:
 * ```typescript\n * {\n *   sessionId: string\n *   nonce: string\n *   latitude: number\n *   longitude: number\n *   accuracy: number // GPS accuracy in meters\n *   credentialId: string\n *   clientDataJSON: string // base64\n *   authenticatorData: string // base64\n *   signature: string // base64\n * }\n * ```\n * \n * **Response**:
 * ```typescript\n * {\n *   checkInId: string\n *   sessionId: string\n *   timestamp: ISO8601\n *   status: 'success' | 'failed'\n *   gates: {\n *     geofence: boolean\n *     cryptographic: boolean\n *     multimodal: boolean\n *     nonce: boolean\n *     biometric: boolean\n *     device: boolean\n *   }\n *   message: string\n * }\n * ```\n * \n * ### GET /api/curriculum/resources/{sessionId}\n * \n * **Response**:
 * ```typescript\n * UnlockedResource[] = [\n *   {\n *     id: string\n *     sessionId: string\n *     title: string\n *     type: 'pdf' | 'slides' | 'video' | 'quiz' | 'assignment'\n *     url: string\n *     unlockedAt: ISO8601\n *     description?: string\n *     metadata?: {\n *       duration?: number // minutes\n *       pages?: number\n *       points?: number\n *     }\n *   }\n * ]\n * ```\n * \n * ### GET /api/analytics/performance\n * \n * **Response**:
 * ```typescript\n * {\n *   attendanceRate: number // 0-100\n *   curriculumEngagement: number // 0-100\n *   riskScore: number // 0-100 (100 = safe, 0 = risky)\n * }\n * ```\n * \n * ## Error Scenarios & Handling\n * \n * | Scenario | Component | Handling |\n * |----------|-----------|----------|\n * | API down | LiveSessionsWidget | Falls back to MOCK_SESSIONS |\n * | No geolocation | MarkAttendanceFlow | Shows error, lets user retry |\n * | WebAuthn unavailable | MarkAttendanceFlow | Mocks response |\n * | Check-in fails | MarkAttendanceFlow | Shows error state, allows retry |\n * | Curriculum fetch fails | StudentCurriculumView | Shows error boundary |\n * | Analytics API down | StudentPerformanceRadar | Uses mock data with warning |\n * | Component crash | Any | ErrorBoundary catches + retry |\n * \n * ## Performance Optimizations\n * \n * 1. **Query Caching**:\n *    - Sessions: 2 min stale time\n *    - Curriculum: 5 min stale time\n *    - Analytics: 5 min stale time\n * \n * 2. **Lazy Loading**:
 *    - Router uses lazy() for page components
 *    - Suspense boundaries with loading state\n * \n * 3. **Animation Optimization**:
 *    - CSS animations (not JS) for slide-in\n *    - GPU-accelerated transforms\n * \n * 4. **Bundle Optimization**:
 *    - Tree-shaking removes unused code\n *    - Recharts is dynamic import candidate\n * \n * ## Testing Strategy\n * \n * ### Component Tests\n * ```typescript\n * // Test error boundaries catch errors\n * render(<ErrorBoundary><Component /></ErrorBoundary>)\n * expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()\n * \n * // Test graceful fallback\n * mockAttendanceAPI.getSessions.mockRejectedValue(new Error())\n * render(<LiveSessionsWidget />)\n * expect(screen.getByText(/using mock data/i)).toBeInTheDocument()\n * \n * // Test attendance flow state management\n * render(<MarkAttendanceFlow sessionId=\"123\" isOpen={true} />)\n * expect(store.selectedSessionId).toBe('123')\n * ```\n * \n * ## Security Considerations\n * \n * 1. **Zero-Trust Verification**:
 *    - 6-gate conjunction: all must pass\n *    - Geofence + Cryptographic + Multimodal + Nonce + Biometric + Device\n * \n * 2. **WebAuthn**:
 *    - Hardware key binding prevents replay\n *    - Nonce prevents reuse\n * \n * 3. **Data Privacy**:
 *    - Biometric: outcome only, never raw data\n *    - Location: only during check-in window\n *    - No local storage of sensitive credentials\n * \n * 4. **API Security**:
 *    - All endpoints require authentication\n *    - Axios interceptor adds Authorization header\n *    - CSRF tokens if applicable\n * \n * ## Browser Compatibility\n * \n * - Chrome/Edge 90+\n * - Firefox 88+\n * - Safari 14+\n * - Requires:\n *   - Geolocation API\n *   - WebAuthn (with fallback)\n *   - CSS Grid & Flexbox\n * \n * ## Future Enhancements\n * \n * 1. **Offline Mode**: Service Worker caching\n * 2. **Progressive Disclosure**: Collapsible sections\n * 3. **Custom Themes**: Dark mode toggle\n * 4. **Accessibility**: ARIA labels, keyboard nav\n * 5. **Mobile Optimization**: Touch-friendly interactions\n * 6. **Real-time Updates**: WebSocket notifications\n * 7. **Advanced Analytics**: Drill-down into metrics\n * 8. **Curriculum Search**: Filter and search resources\n */\n