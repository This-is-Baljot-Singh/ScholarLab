import { RouterProvider } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { router } from '@/router/routes';
import { queryClient } from '@/config/queryClient';
import '@/index.css';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster position="top-center" richColors />
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

export default App;
