import { useCallback, useState } from 'react';
import { toast } from 'sonner';

export interface GeolocationCoordinates {
  latitude: number;
  longitude: number;
  accuracy: number;
  altitude?: number;
  altitudeAccuracy?: number;
  heading?: number;
  speed?: number;
}

export const useGeolocation = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getLocation = useCallback(
    (): Promise<GeolocationCoordinates | null> => {
      return new Promise((resolve) => {
        if (!navigator.geolocation) {
          const errorMsg = 'Geolocation is not supported by your browser';
          setError(errorMsg);
          toast.error(errorMsg);
          resolve(null);
          return;
        }

        setIsLoading(true);
        setError(null);

        navigator.geolocation.getCurrentPosition(
          (position) => {
            const coords: GeolocationCoordinates = {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy,
              altitude: position.coords.altitude ?? undefined,
              altitudeAccuracy: position.coords.altitudeAccuracy ?? undefined,
              heading: position.coords.heading ?? undefined,
              speed: position.coords.speed ?? undefined,
            };
            setIsLoading(false);
            resolve(coords);
          },
          (err) => {
            setIsLoading(false);
            let errorMsg = 'Failed to get your location';

            switch (err.code) {
              case err.PERMISSION_DENIED:
                errorMsg = 'Location permission denied. Please enable location in settings.';
                break;
              case err.POSITION_UNAVAILABLE:
                errorMsg = 'Location information is unavailable. Please try again.';
                break;
              case err.TIMEOUT:
                errorMsg = 'The request to get your location timed out. Please try again.';
                break;
            }

            setError(errorMsg);
            toast.error(errorMsg);
            resolve(null);
          },
          {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
          }
        );
      });
    },
    []
  );

  return { getLocation, isLoading, error };
};
