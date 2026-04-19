# ScholarLab - Frontend

Enterprise educational platform built with React 18, Vite, TypeScript, and Tailwind CSS.

## Technology Stack

- **Framework**: React 18 with Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **Routing**: React Router v6
- **State Management**: Zustand (client state) + TanStack Query (server state)
- **API**: Axios with JWT interceptor and automatic token refresh
- **Icons**: Lucide React

## Project Structure

```
src/
├── features/                  # Feature-based modules
│   ├── auth/                 # Authentication feature
│   │   ├── components/       # Auth components (ProtectedRoute)
│   │   ├── hooks/           # useAuth hooks
│   │   └── pages/           # Auth pages (Login, etc.)
│   ├── attendance/           # Attendance management
│   │   ├── components/
│   │   └── pages/
│   └── curriculum/           # Curriculum management
│       ├── components/
│       └── pages/
├── shared/                   # Shared components and utilities
│   ├── components/          # Reusable UI components
│   ├── hooks/              # Custom React hooks
│   ├── layouts/            # Layout wrappers (MainLayout, AuthLayout)
│   └── ui/                 # shadcn/ui base components
├── api/                     # API client and interceptors
│   └── client.ts           # Axios instance with JWT handling
├── store/                   # Zustand stores
│   └── authStore.ts        # Authentication state store
├── router/                  # Route configuration
│   └── routes.tsx          # React Router setup with protected routes
├── config/                  # Configuration files
│   └── queryClient.ts      # React Query setup
├── types/                   # TypeScript type definitions
│   └── auth.ts             # Auth-related types
├── constants/              # Application constants
│   └── auth.ts             # Auth constants (roles, tokens keys)
└── App.tsx                 # Root component
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Configuration

Create a `.env` file based on `.env.example`:

```bash
VITE_API_URL=http://localhost:8000/api
```

### 3. Running the Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### 4. Build for Production

```bash
npm run build
```

### 5. Preview Production Build

```bash
npm run preview
```

## Authentication & Authorization

### User Roles

The application supports three user roles:
- **Student**: Access to dashboard, attendance, and curriculum
- **Faculty**: Access to dashboard, attendance, curriculum, and student management
- **Admin**: Full platform access including admin panel

### JWT Token Handling

The Axios client (`src/api/client.ts`) includes:
- **Request Interceptor**: Automatically injects JWT tokens from localStorage
- **Response Interceptor**: Handles automatic token refresh on 401 errors
- **Token Refresh Flow**: Queues requests while refreshing, then retries with new token

### Storing Credentials Securely

Tokens are stored in localStorage. For production, consider:
- Using httpOnly cookies (requires backend support)
- Implementing secure token storage mechanisms
- Using authentication libraries like Auth0 or AWS Cognito

## State Management

### Client State (Zustand)
- User authentication state
- User information and roles
- Auth errors

**Location**: `src/store/authStore.ts`

Use it:
```typescript
import { useAuthStore } from '@/store/authStore';

const user = useAuthStore((state) => state.user);
const login = useAuthStore((state) => state.login);
```

### Server State (React Query)
- API data caching
- Automatic refetching
- Background synchronization

**Location**: `src/config/queryClient.ts`

Configure in `src/App.tsx` as `<QueryClientProvider>`

## Protected Routes

Routes are protected using the `<ProtectedRoute>` component:

```typescript
<ProtectedRoute requiredRoles={[USER_ROLES.ADMIN]}>
  <AdminPanel />
</ProtectedRoute>
```

## Styling

### Tailwind CSS
- Custom color palette (Indigo/Blue primary, Slate neutral)
- Typography using Inter font family
- Refined shadow system for enterprise look

### Component Classes
Pre-defined utility classes in `src/index.css`:
- `.btn-primary`, `.btn-secondary`, `.btn-outlined`
- `.card` for card containers
- `.input` for form inputs

## API Integration

### Making API Requests

```typescript
import { apiClient } from '@/api/client';

// GET request
const response = await apiClient.get('/endpoint');

// POST request
const response = await apiClient.post('/endpoint', { data });

// With React Query
import { useQuery } from '@tanstack/react-query';

const { data, isLoading } = useQuery({
  queryKey: ['endpoint'],
  queryFn: () => apiClient.get('/endpoint'),
});
```

## Development Workflow

1. **Feature Development**: Create feature folders under `src/features/`
2. **Component Creation**: Use Tailwind + shadcn/ui for consistency
3. **API Integration**: Use React Query for server state
4. **State Management**: Use Zustand for client state
5. **Type Safety**: Always define types in `src/types/`

## Next Steps

1. Install shadcn/ui components as needed
2. Create actual page components for each feature
3. Implement login page UI
4. Add form validation (use libraries like Zod or Yup)
5. Set up error handling and toast notifications
6. Configure API endpoints to match backend

## Resources

- [React Documentation](https://react.dev)
- [Vite Documentation](https://vitejs.dev)
- [React Router Documentation](https://reactrouter.com)
- [Tailwind CSS Documentation](https://tailwindcss.com)
- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Axios Documentation](https://axios-http.com)
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
