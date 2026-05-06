import { useNavigate } from 'react-router-dom';
import { StudentRiskPostureModal } from '@/features/attendance/components';

export const StudentRiskPosturePage = () => {
  const navigate = useNavigate();

  return (
    <StudentRiskPostureModal
      isOpen={true}
      variant="page"
      onClose={() => {
        navigate('/student/overview');
      }}
    />
  );
};