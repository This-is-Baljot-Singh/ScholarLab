# ScholarLab Frontend - Architecture Overview

## System Design

### Authentication & Authorization Flow

```
Browser
  ↓
Login Form → apiClient.post('/auth/login')
  ↓
JWT Tokens Stored (localStorage)
  ↓
useAuthStore updated (Zustand)
  ↓
Redirect to protected route
  ↓
ProtectedRoute checks authentication
  ↓
Sidebar renders role-based navigation
```

### Request/Response Cycle

```
Component
  ↓
useQuery/useMutation (React Query)
  ↓
apiClient.get/post() (Axios)
  ↓
Request Interceptor
  ├─ Inject: Authorization: Bearer {token}
  ├─ Set: Content-Type: application/json
  └─ Continue to API
  ↓
API Server (Backend)
  ↓
Response (success/error)
  ↓
Response Interceptor
  ├─ If 401 → Auto-refresh token
  ├─ If refresh fails → Logout
  └─ Retry request or return error
  ↓
Component receives data
  ↓
UI renders with React Query cache
```

### State Management Strategy

#### Client State (Zustand)
- `useAuthStore`: User auth state, tokens
- Persistent storage via localStorage
- Accessed via hooks: `useAuthUser()`, `useIsAuthenticated()`

#### Server State (React Query)
- API response caching
- Automatic refetching
- Background synchronization
- Devtools integration (install @tanstack/react-query-devtools)

### Module Dependencies

```
App.tsx
├─ QueryClientProvider (React Query)
├─ RouterProvider (React Router)
│  └─ MainLayout/AuthLayout
│     ├─ TopAppBar (uses auth hooks)
│     ├─ Sidebar (uses auth hooks, useLocation)
│     └─ Route children (protected via ProtectedRoute)
│
├─ ProtectedRoute
│  └─ useAuthUser(), useUserRole()
│
├─ useAuth hooks
│  └─ apiClient, useAuthStore
│
└─ apiClient
   └─ axiosInstance with interceptors
      └─ useAuthStore (auto-refresh)
```

## Data Flow Examples

### Example 1: User Login

```typescript
// LoginPage.tsx
const { mutate: login } = useLogin();

login({ email, password });
  ↓
Mutation triggers:
  1. useLogin calls apiClient.post('/auth/login')
  2. useAuthStore.login() updates state
  3. Tokens stored in localStorage
  4. Navigate to dashboard
  5. ProtectedRoute checks → allows entry
```

### Example 2: Authenticated API Request

```typescript
// DashboardPage.tsx
const { data: dashboard } = useQuery({
  queryKey: ['dashboard'],
  queryFn: () => apiClient.get('/dashboard')
});

Request:
  1. apiClient interceptor injects Bearer token
  2. Server validates token
  3. Returns data
  4. React Query caches result
  5. Component renders

If token expired:
  1. Server returns 401
  2. Interceptor detects 401
  3. Queue pending requests
  4. Call /auth/token/refresh
  5. Update accessToken in store & localStorage
  6. Retry original request with new token
  7. Return cached data
```

### Example 3: Role-Based Navigation

```typescript
// TopAppBar.tsx
const userRole = useUserRole(); // Gets from useAuthStore

const navLinks = [
  { path: '/admin', roles: [ADMIN] },
  { path: '/attendance', roles: [STUDENT, FACULTY, ADMIN] },
];

filteredLinks = navLinks.filter(link =>
  !userRole || link.roles.includes(userRole)
);

// Only renders allowed links for user's role
```

## Security Considerations

### ✅ Implemented
- JWT token injection in requests
- Automatic token refresh
- Protected routes with role checks
- Logout on auth failure
- Type-safe token handling

### 🔐 Recommended for Production
- Move tokens to httpOnly cookies (backend collaboration)
- Implement CSRF token handling
- Add request signing/verification
- Use secure session management
- Implement audit logging
- Add rate limiting awareness
- Use Content Security Policy headers

### 🛡️ Token Lifecycle
```
User Login
  ↓
Server returns: { accessToken (short-lived), refreshToken (long-lived) }
  ↓
Store tokens in localStorage
  ↓
Each request injects accessToken
  ↓
When token expires (401):
  ├─ Queue pending requests
  ├─ Use refreshToken to get new accessToken
  ├─ Update stored tokens
  └─ Retry queued requests
  ↓
If refresh fails:
  ├─ Clear all tokens
  ├─ Update auth state
  └─ Redirect to login
```

## Performance Optimizations

### 1. Code Splitting
- Feature-based components enable per-feature bundles
- React Router lazy loading support ready

### 2. Caching Strategy
- React Query: 5-minute stale time, 10-minute cache time
- Browser cache for static assets
- IndexedDB ready for large datasets

### 3. Bundle Size
- Tree-shaking with ES modules
- Type-only imports for unused types
- Dynamic imports for heavy dependencies

### 4. Network
- Request batching via React Query
- Automatic retry with exponential backoff
- Connection state awareness

## Extension Points

### Adding New Features
```
1. Create feature folder: src/features/[feature]/
2. Add structure:
   ├─ components/
   ├─ pages/
   ├─ hooks/
   ├─ types/
   └─ queries/ (if using React Query)
3. Register routes in src/router/routes.tsx
4. Add role-based access if needed
```

### Adding API Hooks
```typescript
// src/features/[feature]/hooks/useXXX.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export const useGetData = () => useQuery({
  queryKey: ['data'],
  queryFn: () => apiClient.get('/endpoint'),
});

export const useCreateData = () => useMutation({
  mutationFn: (data) => apiClient.post('/endpoint', data),
  onSuccess: () => queryClient.invalidateQueries(['data']),
});
```

### Adding Protected Routes
```typescript
// In routes.tsx
{
  path: '/admin/users',
  element: (
    <MainLayout>
      <ProtectedRoute requiredRoles={[USER_ROLES.ADMIN]}>
        <UserManagementPage />
      </ProtectedRoute>
    </MainLayout>
  ),
}
```

## Debugging

### Enable React Query DevTools
```typescript
// src/App.tsx
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

### Check Auth State
```typescript
// Browser console
import { useAuthStore } from '@/store/authStore';
useAuthStore.getState(); // View entire store
useAuthStore.subscribe(console.log); // Watch changes
```

### Monitor API Calls
```typescript
// Browser DevTools Network tab
// All requests will show Authorization header with bearer token
```

## Environment Configurations

### Development
```
VITE_API_URL=http://localhost:8000/api
```

### Staging
```
VITE_API_URL=https://staging-api.scholarlab.com/api
```

### Production
```
VITE_API_URL=https://api.scholarlab.com/api
```

---

**Architecture Version**: 1.0.0
**Last Updated**: April 19, 2026
