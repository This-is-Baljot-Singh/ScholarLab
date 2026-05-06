import { useNavigate } from 'react-router-dom';
import { UnlockedResourcesModal } from '@/features/attendance/components';

export const UnlockedResourcesPage = () => {
  const navigate = useNavigate();

  return (
    <UnlockedResourcesModal
      isOpen={true}
      variant="page"
      onClose={() => {
        navigate('/student/overview');
      }}
    />
  );
};