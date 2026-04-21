# Sprint 4 Analytics: Visual Architecture

## Dashboard Layout Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                   Predictive Analytics Engine                       │
│          Powered by XGBoost & Spatial Telemetry                    │
└────────────────────────────────────────────────────────────────────┘

┌──────────────┬──────────────┬──────────────┬──────────────┐
│   412        │     87%      │      18      │       2      │
│   Active     │   Campus     │  Predicted   │  Spoofing    │
│  Students    │ Attendance   │  At-Risk     │  Attempts    │
└──────────────┴──────────────┴──────────────┴──────────────┘

┌─────────────────────────────────┬──────────────────────────────┐
│  AttendanceTrendsChart          │  Campus Risk Distribution    │
│  ╔═══════════════════════════╗  │  ╔════════════════════════╗  │
│  ║        Attendance         ║  │  ║   Safe  (394)          ║  │
│  ║   45 ╱╲                   ║  │  ║   ╱╲╲                  ║  │
│  ║   40 ╱  ╲                 ║  │  ║  ╱ At-Risk (18)        ║  │
│  ║   35╱    ╲╱               ║  │  ║ ╱╲                     ║  │
│  ║   Apr 1  Apr 30           ║  │  ║                        ║  │
│  ╚═══════════════════════════╝  │  ╚════════════════════════╝  │
│  LineChart (Recharts)           │  PieChart (Recharts)         │
│  - 30-day trend                 │  - Donut format               │
│  - Hover tooltip                │  - Green/Red segments         │
│  - Real-time refresh (60s)      │                              │
└─────────────────────────────────┴──────────────────────────────┘

┌─────────────────────────────────┬──────────────────────────────┐
│  Live Inference Demo            │  At-Risk Students List       │
│  ╔═════════════════════════╗    │  ╔════════════════════════╗  │
│  ║ Sample Student Vector   ║    │  ║ 🔴 Rajesh Kumar (78%) ║  │
│  ║         Safe  ⭕        ║    │  ║    Critical            │  │
│  ║                         ║    │  ║ 🟡 Priya Singh (62%)   ║  │
│  ║ XGBoost Risk Score: 35% ║    │  ║    At Risk → Click     ║  │
│  ║ ████░░░░░░░░░░░░░░░░░░░║    │  ║ 🟡 Amit Patel (55%)    ║  │
│  ║                         ║    │  ║    At Risk → Click     ║  │
│  ║ Attendance: 87% | Cur..║    │  ╚════════════════════════╝  │
│  ╚═════════════════════════╝    │  Interactive list             │
│  Risk probability widget        │  Color-coded severity         │
│                                 │  Modal trigger on click       │
└─────────────────────────────────┴──────────────────────────────┘
                                   ↓ Click student
                    ┌──────────────────────────────────┐
                    │   StudentRiskModal (Portal)      │
                    ├──────────────────────────────────┤
                    │ Student Risk Analysis            │
                    │ Rajesh Kumar                     │
                    ├──────────────────────────────────┤
                    │ Risk Probability: 78%   🔴       │
                    │                                  │
                    │ SHAP Feature Impact Chart:       │
                    │ ╔════════════════════════════╗  │
                    │ ║ ATTENDANCE_RATE ████░░░░─ │  │
                    │ ║ (value: 0.65)     [Green] │  │
                    │ ║ ✓ Decreases risk by 0.12  │  │
                    │ ║                            │  │
                    │ ║ LATE_SUBMISSIONS ██░░░░░░ │  │
                    │ ║ (value: 4)        [Red]   │  │
                    │ ║ ✗ Increases risk by 0.18  │  │
                    │ ║                            │  │
                    │ ║ CURRICULUM_ENGAGEMENT ... │  │
                    │ ║ (value: 2.1)      [Green] │  │
                    │ ║ ✓ Decreases risk by 0.08  │  │
                    │ ╚════════════════════════════╝  │
                    │                                  │
                    │ [← Close]                        │
                    └──────────────────────────────────┘
```

## SHAP Bar Chart - Color Legend

```
🟢 GREEN BARS = Variables DECREASING Risk
   ├─ High attendance rate → ✓ Lower risk
   ├─ Recent assignments submitted → ✓ Lower risk
   └─ Active curriculum engagement → ✓ Lower risk

🔴 RED BARS = Variables INCREASING Risk
   ├─ Frequent late submissions → ✗ Higher risk
   ├─ Low engagement score → ✗ Higher risk
   └─ High absence count → ✗ Higher risk

Bar Length = Magnitude of Impact
  ████░░░░ = Large impact (0.25–0.35)
  ███░░░░░ = Medium impact (0.10–0.25)
  ██░░░░░░ = Small impact (0.05–0.10)
```

## Data Flow - Request/Response Cycle

```
┌─────────────────┐
│   Faculty User  │
│  Views Dashboard│
└────────┬────────┘
         │
         ↓ ComponentMount
┌──────────────────────────────────────────┐
│  PredictiveAnalyticsDashboard            │
│  useQuery(['ml-analytics-overview'])     │
└────────┬─────────────────────────────────┘
         │
         ↓ GET /api/analytics/overview
         │
    ╔════════════════════════════════════════╗
    ║  BACKEND FastAPI Server                ║
    ║  ╔──────────────────────────────────╗  ║
    ║  │ @router.get("/overview")         │  ║
    ║  │ 1. Query MongoDB attendance logs │  ║
    ║  │ 2. Calculate campus aggregates   │  ║
    ║  │ 3. Sample student vector         │  ║
    ║  │ 4. Run XGBoost prediction        │  ║
    ║  │ 5. Run SHAP explainer            │  ║
    ║  │ 6. Return JSON response          │  ║
    ║  └──────────────────────────────────┘  ║
    ╚════════════════════════════════════════╝
         ↑
         │ Response: {
         │   "campus_aggregate": {...},
         │   "live_inference_demo": {...}
         │ }
         │
    ┌────┴──────────────────────────────────┐
    │                                        │
    ↓ Parse & Render                ↓ Click Student
┌─────────────────────────┐      ┌──────────────────┐
│ AttendanceTrendsChart   │      │ AtRiskStudentList│
│ + StatCards             │      └────────┬─────────┘
│ + CampusRiskDistribution│             │
│ + LiveInferenceDemo     │             ↓ setSelectedStudent
└─────────────────────────┘
                                   StudentRiskModal
                                        ↓
                                GET /api/analytics/predict/risk/
                                         {student_id}
                                        │
                                    ╔═══════════════════════╗
                                    ║ Backend Response:     ║
                                    ║ {                     ║
                                    ║   risk_probability:0.78
                                    ║   shap_explanations:[
                                    ║     {                 ║
                                    ║       feature: "...", ║
                                    ║       shap_impact:... ║
                                    ║     },               ║
                                    ║     ...              ║
                                    ║   ]                 ║
                                    ║ }                    ║
                                    ╚═══════════════════════╝
                                        │
                                        ↓
                                 SHAPExplanationChart
                                 (Horizontal Bar Chart)
                                        │
                                        ↓
                                   Display with colors
```

## Component Dependencies Graph

```
PredictiveAnalyticsDashboard
├── Imports: AttendanceTrendsChart
│   └── Dependencies: Recharts, React Query, Axios
├── Imports: AtRiskStudentsList  
│   └── Dependencies: Lucide icons, React hooks
│       └── Uses: StudentRiskModal
│           └── Dependencies: SHAPExplanationChart
│               └── Dependencies: Recharts, Lucide icons
└── Direct Recharts: PieChart, StatCard
```

## Tech Stack Versions

```
Frontend Libraries:
├── recharts@3.8.1          (Charting)
├── @tanstack/react-query@5.99.2 (Server state)
├── axios@1.15.0            (HTTP client)
├── lucide-react@1.8.0      (Icons)
├── react-dom@19.2.4        (UI rendering)
└── tailwindcss             (Styling)

Backend Stack:
├── FastAPI 0.109+          (API framework)
├── joblib 1.3+             (Model serialization)
├── shap 0.45+              (SHAP explainer)
├── xgboost 2.0+            (ML model)
├── Motor                   (Async MongoDB)
└── PyJWT                   (Token handling)
```

## Performance Metrics

```
Build Output:
✓ 2,623 modules transformed
✓ Assets generated:
  - index.html: 0.45 KB
  - CSS bundle: 60.15 KB (gzip: 14.81 KB)
  - JS bundle: 1,154.33 KB (gzip: 347.33 KB)
✓ Built in 600ms

API Response Times (estimated):
- /analytics/overview: 300-500ms (full calc + SHAP)
- /analytics/predict/risk/{id}: 500-1000ms (XGBoost + SHAP explainer)
- /analytics/dashboard/trends: 100-200ms (aggregation only)

Caching Strategy:
- Attendance trends: 60s refetch interval
- Campus overview: 5min refetch interval
- Student risk: On-demand (user clicks)
```

## Error Boundary Scenarios

```
Network Error
  └─ Fallback: "Failed to load predictive analytics engine"
     └─ User action: Retry or dismiss

Invalid Student ID
  └─ POST /predict/risk/invalid_id → 404
  └─ Modal shows: "Unable to Load Risk Analysis"
     └─ User action: Select different student

No Attendance Data
  └─ Empty trends array
  └─ Chart shows: "No attendance data available"
     └─ User action: Wait for data collection

Authentication Expired
  └─ 401 Unauthorized on API call
  └─ Axios interceptor: Refresh token & retry
  └─ If refresh fails: Redirect to login
```

## Future Enhancements (Post-Sprint 4)

```
Short-term (1-2 sprints):
├─ Real-time WebSocket alerts for new at-risk detections
├─ Intervention logging (faculty notes on students)
├─ Configurable risk score thresholds
└─ CSV/PDF export of trends & risk analyses

Medium-term (2-3 sprints):
├─ Predictive model retraining pipeline
├─ Bulk student actions (email all at-risk)
├─ Calendar heatmap of high-absence days
└─ Student pop-out profile card

Long-term (3+ sprints):
├─ ML model versioning & A/B testing
├─ Automated intervention recommendations
├─ Faculty feedback loop for model improvement
└─ Institution-level benchmarking dashboard
```

