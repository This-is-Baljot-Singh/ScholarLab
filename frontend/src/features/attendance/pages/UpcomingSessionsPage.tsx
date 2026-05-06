import { useNavigate } from 'react-router-dom';
import { UpcomingSessionsModal } from '@/features/attendance/components';

export const UpcomingSessionsPage = () => {
  const navigate = useNavigate();

  return (
    <UpcomingSessionsModal
      isOpen={true}
      variant="page"
      onClose={() => {
        navigate('/student/overview');
      }}
    />
  );
};