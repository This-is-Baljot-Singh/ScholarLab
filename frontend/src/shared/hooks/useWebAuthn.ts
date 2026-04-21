// ScholarLab/frontend/src/shared/hooks/useWebAuthn.ts
import { useCallback, useState } from 'react';
import { toast } from 'sonner';
import { startRegistration, startAuthentication } from '@simplewebauthn/browser';
import type { 
  AuthenticationResponseJSON, 
  RegistrationResponseJSON 
} from '@simplewebauthn/browser'; // Brings in strict typing for the cryptograms
import { apiClient } from '@/lib/api';

export interface WebAuthnCredential {
  id: string;
  type: string;
  transports?: string[];
  name?: string;
}

export const useWebAuthn = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. Device Registration (Setup Phase)
  const registerDevice = useCallback(async (email: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Request cryptographic challenge from FastAPI
      const { data: options } = await apiClient.post('/api/auth/webauthn/register/options', { email });
      
      // Invoke native biometric prompt (FaceID, Windows Hello, TouchID)
      const attestationResponse: RegistrationResponseJSON = await startRegistration(options);
      
      // Send the signed cryptogram back to FastAPI for storage
      await apiClient.post('/api/auth/webauthn/register/verify', {
        email,
        credential: attestationResponse
      });
      
      toast.success('Biometric device registered successfully!');
      return true;
    } catch (err: any) {
      console.error("WebAuthn Registration Error:", err);
      const errorMessage = err.message || 'Device registration failed';
      setError(errorMessage);
      toast.error(errorMessage);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 2. Proof of Presence (Attendance Phase)
  const authenticate = useCallback(async (email: string): Promise<AuthenticationResponseJSON | null> => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Fetch fresh challenge for this specific attendance session
      const { data: options } = await apiClient.post('/api/auth/webauthn/authenticate/options', { email });
      
      // Request user's biometric signature
      const assertionResponse: AuthenticationResponseJSON = await startAuthentication(options);
      
      toast.success('Identity verified locally');
      return assertionResponse; 
    } catch (err: any) {
      console.error("WebAuthn Auth Error:", err);
      const errorMessage = err.message || 'Biometric verification failed';
      setError(errorMessage);
      toast.error(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { registerDevice, authenticate, isLoading, error };
};