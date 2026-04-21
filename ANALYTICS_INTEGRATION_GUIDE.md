# Frontend Analytics Integration Guide

## Component Hierarchy

```
FacultyPortal
├── FacultyDashboardPage
│   └── PredictiveAnalyticsDashboard (Main container)
│       ├── StatCard × 4 (Top metrics)
│       │   ├── Active Students
│       │   ├── Campus Attendance %
│       │   ├── Predicted At-Risk
│       │   └── Spoofing Attempts
│       │
│       ├── AttendanceTrendsChart (LEFT)
│       │   └── LineChart (Recharts)
│       │       ├── X-axis: Date (MM/DD format)
│       │       ├── Y-axis: Verified Attendances
│       │       └── Tool-tip on hover
│       │
│       ├── Campus Risk Distribution (RIGHT)
│       │   └── PieChart (Recharts)
│       │       ├── Safe (Green, #10b981)
│       │       └── At Risk (Red, #ef4444)
│       │
│       ├── Live Inference Demo (BOTTOM-LEFT)
│       │   └── Risk Score Progress Bar
│       │       ├──Telemetry Cards
│       │       └── Classification Badge
│       │
│       └── AtRiskStudentsList (BOTTOM-RIGHT)
│           ├── Student Cards × N
│           │   ├── Risk Level Badge
│           │   ├── Risk % Score
│           │   └── Last Seen Time
│           │
│           └── StudentRiskModal (Portal)
│               ├── Risk Probability Gauge
│               └── SHAPExplanationChart
│                   └── BarChart (Horizontal)
│                       ├── Features (Y-axis)
│                       ├── Impact Magnitude (X-axis)
│                       └── Color: Red (↑ risk) | Green (↓ risk)
```

## API Integration Points

### 1. Attendance Trends (`GET /analytics/dashboard/trends`)
```javascript
// AttendanceTrendsChart.tsx
useQuery({
  queryKey: ['attendance-trends'],
  queryFn: async () => {
    const response = await apiClient.get('/analytics/dashboard/trends');
    return response.data; // [{ date: "2026-04-20", count: 45 }, ...]
  },
  refetchInterval: 60000, // 1 minute
})
```

**Response Format**:
```json
[
  { "date": "2026-04-01", "count": 32 },
  { "date": "2026-04-02", "count": 38 },
  ...
]
```

### 2. Campus Overview (`GET /analytics/overview`)
```javascript
// PredictiveAnalyticsDashboard.tsx
useQuery({
  queryKey: ['ml-analytics-overview'],
  queryFn: async () => {
    const response = await apiClient.get('/analytics/overview');
    return response.data;
  },
  refetchInterval: 300000, // 5 minutes
})
```

**Response Format**:
```json
{
  "campus_aggregate": {
    "total_students_tracked": 342,
    "current_attendance_rate": 87,
    "students_at_risk": 18,
    "recent_spoofing_attempts": 2
  },
  "live_inference_demo": {
    "classification": "Safe" | "At Risk",
    "risk_score_percentage": 35,
    "telemetry_used": {
      "attendance_rate": 0.87,
      "curriculum_engagement_score": 7.2
    }
  }
}
```

### 3. Student Risk Prediction (`POST /analytics/predict/risk/{user_id}`)
```javascript
// StudentRiskModal.tsx
useQuery({
  queryKey: ['student-risk', studentId],
  queryFn: async () => {
    const response = await apiClient.post(`/analytics/predict/risk/${studentId}`);
    return response.data;
  },
  enabled: isOpen && !!studentId,
})
```

**Request**:
```
POST /api/analytics/predict/risk/student_001
```

**Response Format**:
```json
{
  "user_id": "student_001",
  "risk_label": 1,
  "risk_probability": 0.78,
  "shap_explanations": [
    {
      "feature": "attendance_rate",
      "value": 0.65,
      "shap_impact": -0.12,
      "human_readable": "The 'attendance_rate' variable decreased the risk score by 0.120 points."
    },
    {
      "feature": "late_submissions",
      "value": 4,
      "shap_impact": 0.18,
      "human_readable": "The 'late_submissions' variable increased the risk score by 0.180 points."
    },
    ...
  ]
}
```

## Component State Flows

### AttendanceTrendsChart
```
useQuery({
  status: 'loading' | 'success' | 'error'
})
         ↓
    isLoading? → Show spinner
         ↓
    isError?   → Show error message
         ↓
    trends[]   → Map to <LineChart> data
         ↓
    <ResponsiveContainer> → Fit to parent width
```

### SHAPExplanationChart
```
Input Props:
  - explanations: SHAPExplanation[]
  - riskProbability: number (0-1)
         ↓
useMemo(() => {
  - Sort by |shap_impact| descending
  - Calculate color: impact > 0 ? red : green
  - Normalize feature_names (attendance_rate → ATTENDANCE RATE)
})
         ↓
   <BarChart layout="vertical">
     - X-axis: Impact magnitude
     - Y-axis: Feature names
     - Colors: Red (increasing risk) | Green (decreasing risk)
   </BarChart>
```

### StudentRiskModal
```
Props: {
  studentId, studentName, isOpen, onClose
}
         ↓
isOpen=false → Return null (unmount)
         ↓
isOpen=true → Show backdrop + modal
         ↓
useQuery([student-risk, studentId]) →
  isLoading?  → <Loader2 spinner>
  isError?    → <AlertCircle> error text
  success?    → <SHAPExplanationChart data={prediction}>
         ↓
  User clicks "Close" → onClose() → isOpen=false
```

### AtRiskStudentsList
```
Input Props: students[] (demo data)
         ↓
useState: selectedStudent, isModalOpen
         ↓
students.map((student) => (
  <button onClick={() => handleStudentClick(student.id)}>
    <StudentCard risk={student.riskScore} />
  </button>
))
         ↓
handleStudentClick() →
  setSelectedStudent(id)
  setIsModalOpen(true)
         ↓
<StudentRiskModal studentId={selectedStudent} isOpen={isModalOpen}>
```

## Styling & Theming

### Color Scheme
```
Safe (< 50%):        🟢 #10b981 (emerald-500)
At Risk (50-70%):    🟡 #f59e0b (amber-500)
Critical (> 70%):    🔴 #ef4444 (red-500)

Primary:             #4f46e5 (indigo-600)
Borders:             #e2e8f0 (slate-200)
Text Primary:        #0f172a (slate-900)
Text Secondary:      #64748b (slate-600)
Background Neutral:  #f1f5f9 (slate-100)
```

### Card Styling
```
border border-slate-200
rounded-xl
bg-white
p-6
shadow-sm
hover:shadow-md (on interactive elements)
```

### Recharts Styling
```
CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0"
Tooltip:
  backgroundColor: '#f8fafc'
  border: '1px solid #e2e8f0'
  borderRadius: '0.5rem'
```

## Responsive Design

### Breakpoints
```
Mobile (< 640px):
  - 1 column layout
  - Full-width charts
  - Stack cards vertically

Tablet (640-1024px):
  - 2 column layout
  - Charts side-by-side

Desktop (> 1024px):
  - 4 stat cards in row
  - 2×2 grid for main charts
  - Full-height layout
```

**Grid Definition**:
```tsx
<div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
  {/* Auto-adjusts: 1 col mobile, 2 col tablet, 4 col desktop */}
</div>
```

## Error Handling Patterns

### No Data Available
```tsx
{isLoading && <Loader2 animate-spin />}
{isError && <AlertCircle /> + "Failed to load..."}
{!data || data.length === 0 && <p>No attendance data available</p>}
```

### Invalid Student ID
```tsx
// Modal calls /predict/risk/{id}
// If 404: useQuery isError=true
// → Show: "Unable to Load Risk Analysis"
```

## Performance Optimizations

### 1. React Query Caching
```javascript
// Attendance trends: cached, refetch every 60s
// Campus overview: cached, refetch every 5 min
// Student risk: cached per studentId, no auto-refetch
```

### 2. useMemo for Chart Data
```javascript
const chartData = useMemo(() => {
  return explanations.sort(...).map(...);
}, [explanations]);
// Prevents unnecessary re-renders
```

### 3. Lazy Modal
```javascript
{selectedStudent && (
  <StudentRiskModal isOpen={isModalOpen} />
)}
// Only renders when student is selected
```

## Testing the Integration

### 1. Check Trends Chart
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/analytics/dashboard/trends
# Should return: [{"date": "...", "count": N}, ...]
```

### 2. Test Student Risk Modal
```typescript
// In browser console
const response = await fetch(
  'http://localhost:8000/api/analytics/predict/risk/student_001',
  { method: 'POST', 
    headers: { 'Authorization': `Bearer ${token}` } 
  }
);
const data = await response.json();
console.log(data.shap_explanations); // Should have 4-5 features
```

### 3. Visual Regression
- Chart axes labels readable?
- Icons properly aligned?
- Colors distinguish risk levels?
- Modal closes without errors?

## Known Issues & TODOs

1. **Real Data**: Currently shows dummy data, needs backend integration
2. **WebSocket Updates**: Risk alerts should push via Socket.IO
3. **Bulk Actions**: Select multiple at-risk students for intervention
4. **Export**: Download trends/risk analysis as CSV/PDF
5. **Thresholds**: Configurable risk score boundaries

