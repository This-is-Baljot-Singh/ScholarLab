import { QueryClient } from '@tanstack/react-query';
import type {
  DefaultOptions,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';

const queryConfig: DefaultOptions = {
  queries: {
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes (formerly cacheTime)
    retry: 1,
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
  },
  mutations: {
    retry: 1,
  },
};

export const queryClient = new QueryClient({
  defaultOptions: queryConfig,
});

declare global {
  interface Array<T> {
    includes(searchElement: T, fromIndex?: number): boolean;
  }
}

export type QueryOptions<T> = Omit<UseQueryOptions<T>, 'queryKey' | 'queryFn'>;
export type MutationOptions<T, V> = Omit<UseMutationOptions<T, Error, V>, 'mutationFn'>;
