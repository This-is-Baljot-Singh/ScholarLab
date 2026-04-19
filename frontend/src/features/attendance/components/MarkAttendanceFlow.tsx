import React, { useState } from 'react';
import { MapPin, Fingerprint, AlertCircle, Loader } from 'lucide-react';
import { BottomSheet } from '@/shared/ui/BottomSheet';
import { BiometricVerificationSkeleton } from '@/shared/ui/SkeletonLoader';
import { useGeolocation, useWebAuthn } from '@/shared/hooks';
import { apiClient } from '@/lib/api';
import type { AuthenticationResponseJSON } from '@simplewebauthn/browser';

interface MarkAttendanceFlowProps {
  isOpen: boolean;
  sessionId: string;
  geofenceId: string;
  userEmail: string;
  onClose: () => void;
  onSuccess: (data: any) => void;
}

type Step = 'location' | 'biometric' | 'submitting' | 'success' | 'error';

export const MarkAttendanceFlow: React.FC<MarkAttendanceFlowProps> = ({
  isOpen,
  sessionId,
  geofenceId,
  userEmail,
  onClose,
  onSuccess,
}) => {
  const [step, setStep] = useState<Step>('location');
  const [error, setError] = useState<string | null>(null);
  const { getLocation, isLoading: locationLoading } = useGeolocation();
  const { authenticate, isLoading: bioLoading } = useWebAuthn();

  const [verificationData, setVerificationData] = useState<{
    latitude?: number;
    longitude?: number;
    accuracy?: number;
    cryptographic_signature?: AuthenticationResponseJSON;
  }>({});

  const handleLocationStep = async () => {
    const coords = await getLocation();
    if (coords) {
      setVerificationData((prev) => ({
        ...prev,
        latitude: coords.latitude,
        longitude: coords.longitude,
        accuracy: coords.accuracy,
      }));
      setStep('biometric');
    } else {
      setError('Failed to secure GPS lock. Ensure high-accuracy mode is active.');
      setStep('error');
    }
  };

  const handleBiometricStep = async () => {
    const credential = await authenticate(userEmail);
    if (credential) {
      setVerificationData((prev) => ({
        ...prev,
        cryptographic_signature: credential,
      }));
      await submitAttendance(credential);
    } else {
      setError('Biometric challenge failed or cancelled.');
      setStep('error');
    }
  };

  const submitAttendance = async (credential: AuthenticationResponseJSON) => {
    setStep('submitting');
    try {
      const payload = {
        session_id: sessionId,
        geofence_id: geofenceId,
        latitude: verificationData.latitude,
        longitude: verificationData.longitude,
        cryptographic_signature: credential,
      };

      const response = await apiClient.post('/attendance/verify', payload);
      setStep('success');
      onSuccess(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Cryptographic verification failed.');
      setStep('error');
    }
  };

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} height="large">
      {step === 'location' && (
        <LocationVerificationStep
          isLoading={locationLoading}
          onNext={handleLocationStep}
          onCancel={onClose}
        />
      )}

      {step === 'biometric' && (
        <BiometricVerificationStep
          isLoading={bioLoading}
          onNext={handleBiometricStep}
          onCancel={onClose}
        />
      )}

      {step === 'submitting' && (
        <div className="flex flex-col items-center justify-center space-y-4 py-12">
          <Loader className="h-12 w-12 animate-spin text-indigo-600" />
          <h3 className="text-lg font-semibold text-slate-900">Verifying Cryptography & Spatial Rules...</h3>
        </div>
      )}

      {step === 'success' && <SuccessStep onClose={onClose} />}

      {step === 'error' && (
        <ErrorStep error={error} onRetry={() => setStep('location')} onClose={onClose} />
      )}
    </BottomSheet>
  );
};

// Location Verification Step
const LocationVerificationStep: React.FC<{
  isLoading: boolean;
  onNext: () => void;
  onCancel: () => void;
}> = ({ isLoading, onNext, onCancel }) => (
  <div className="space-y-6">
    <div className="flex justify-center">
      <div className="rounded-full bg-blue-100 p-4">
        <MapPin className="h-12 w-12 text-blue-600" />
      </div>
    </div>

    <div>
      <h3 className="mb-2 text-lg font-semibold text-slate-900">
        Enable Location Access
      </h3>
      <p className="text-sm text-slate-600">
        We need access to your high-accuracy location to verify attendance at the lecture venue.
      </p>
    </div>

    <div className="rounded-lg bg-blue-50 p-4">
      <p className="text-xs text-blue-800">
        📍 Your location will only be used for attendance verification and will not be
        stored permanently.
      </p>
    </div>

    <button
      onClick={onNext}
      disabled={isLoading}
      className="h-12 w-full rounded-lg bg-blue-600 font-semibold text-white transition-all duration-200 hover:bg-blue-700 disabled:opacity-50"
    >
      {isLoading ? (
        <span className="flex items-center justify-center gap-2">
          <Loader className="h-4 w-4 animate-spin" />
          Getting Location...
        </span>
      ) : (
        'Continue'
      )}
    </button>

    <button
      onClick={onCancel}
      className="w-full rounded-lg border border-slate-300 py-3 font-semibold text-slate-700 transition-colors hover:bg-slate-50"
    >
      Cancel
    </button>
  </div>
);

// Biometric Verification Step
const BiometricVerificationStep: React.FC<{
  isLoading: boolean;
  onNext: () => void;
  onCancel: () => void;
}> = ({ isLoading, onNext, onCancel }) => (
  <div className="space-y-6">
    {isLoading ? (
      <>
        <div className="flex justify-center">
          <div className="rounded-full bg-indigo-100 p-4">
            <Fingerprint className="h-12 w-12 animate-pulse text-indigo-600" />
          </div>
        </div>
        <BiometricVerificationSkeleton />
      </>
    ) : (
      <>
        <div className="flex justify-center">
          <div className="rounded-full bg-indigo-100 p-4">
            <Fingerprint className="h-12 w-12 text-indigo-600" />
          </div>
        </div>

        <div>
          <h3 className="mb-2 text-lg font-semibold text-slate-900">
            Biometric Verification
          </h3>
          <p className="text-sm text-slate-600">
            Use your face or fingerprint to verify your identity.
          </p>
        </div>

        <div className="rounded-lg bg-indigo-50 p-4">
          <p className="text-xs text-indigo-800">
            🔒 Your biometric data is processed locally on your device and never stored on
            servers.
          </p>
        </div>

        <button
          onClick={onNext}
          className="h-12 w-full rounded-lg bg-indigo-600 font-semibold text-white transition-all duration-200 hover:bg-indigo-700"
        >
          Authenticate with Biometrics
        </button>

        <button
          onClick={onCancel}
          className="w-full rounded-lg border border-slate-300 py-3 font-semibold text-slate-700 transition-colors hover:bg-slate-50"
        >
          Cancel
        </button>
      </>
    )}
  </div>
);

// Success Step
const SuccessStep: React.FC<{ onClose: () => void }> = ({ onClose }) => (
  <div className="space-y-6 py-6">
    <div className="flex justify-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
        <span className="text-3xl">✓</span>
      </div>
    </div>

    <div>
      <h3 className="mb-2 text-center text-xl font-semibold text-slate-900">
        Attendance Marked!
      </h3>
      <p className="text-center text-sm text-slate-600">
        Your attendance has been verified and recorded successfully.
      </p>
    </div>

    <div className="rounded-lg bg-green-50 p-4">
      <p className="text-sm text-green-800">
        🎓 New curriculum materials have been unlocked for this lecture.
      </p>
    </div>

    <button
      onClick={onClose}
      className="h-12 w-full rounded-lg bg-green-600 font-semibold text-white transition-all duration-200 hover:bg-green-700"
    >
      Continue
    </button>
  </div>
);

// Error Step
const ErrorStep: React.FC<{
  error: string | null;
  onRetry: () => void;
  onClose: () => void;
}> = ({ error, onRetry, onClose }) => (
  <div className="space-y-6 py-6">
    <div className="flex justify-center">
      <div className="rounded-full bg-red-100 p-4">
        <AlertCircle className="h-12 w-12 text-red-600" />
      </div>
    </div>

    <div>
      <h3 className="mb-2 text-center text-xl font-semibold text-slate-900">
        Verification Failed
      </h3>
      <p className="text-center text-sm text-slate-600">
        {error || 'Something went wrong. Please try again.'}
      </p>
    </div>

    <button
      onClick={onRetry}
      className="h-12 w-full rounded-lg bg-indigo-600 font-semibold text-white transition-all duration-200 hover:bg-indigo-700"
    >
      Try Again
    </button>

    <button
      onClick={onClose}
      className="w-full rounded-lg border border-slate-300 py-3 font-semibold text-slate-700 transition-colors hover:bg-slate-50"
    >
      Cancel
    </button>
  </div>
);
