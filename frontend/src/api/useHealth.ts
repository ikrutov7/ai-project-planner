import { useQuery } from '@tanstack/react-query';
import { fetchHealth } from './client';

export type BackendStatus = 'checking' | 'ok' | 'down';

export function useHealth() {
  const query = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
    retry: 1,
  });

  if (query.isLoading) {
    return { status: 'checking' as BackendStatus, detail: 'Checking API…' };
  }
  if (query.isError || !query.data) {
    return { status: 'down' as BackendStatus, detail: 'API offline' };
  }
  return { status: 'ok' as BackendStatus, detail: `API ${query.data.status}` };
}
