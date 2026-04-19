// ScholarLab/frontend/src/features/faculty/pages/GeofenceManagementPage.tsx
import React, { useState, useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { GeofenceMap } from '../components';
import type { GeofenceWithMetadata } from '@/types/faculty';
import { apiClient } from '@/lib/api';
import { toast } from 'sonner';

interface GeofenceManagementPageProps {
  onBack: () => void;
}

export const GeofenceManagementPage: React.FC<GeofenceManagementPageProps> = ({ onBack }) => {
  const [geofences, setGeofences] = useState<GeofenceWithMetadata[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch geofences on mount
  useEffect(() => {
    const fetchGeofences = async () => {
      try {
        const { data } = await apiClient.get('/geofences');
        
        // Map backend schema to frontend representation
        const mappedData: GeofenceWithMetadata[] = data.map((g: any) => {
          if (g.type === 'radial') {
            return {
              id: g._id,
              type: 'circle',
              name: g.name,
              buildingCode: g.description || '',
              center: { latitude: g.boundary.coordinates[1], longitude: g.boundary.coordinates[0] }, // Backend is [lon, lat]
              radiusMeters: g.radius,
            };
          } else {
            return {
              id: g._id,
              type: 'polygon',
              name: g.name,
              buildingCode: g.description || '',
              // Remove the duplicate closing coordinate for the UI representation
              coordinates: g.boundary.coordinates[0].slice(0, -1).map((coord: number[]) => ({
                latitude: coord[1],
                longitude: coord[0],
              })),
            };
          }
        });
        setGeofences(mappedData);
      } catch (error) {
        toast.error('Failed to load spatial boundaries');
      } finally {
        setLoading(false);
      }
    };
    fetchGeofences();
  }, []);

  const handleSaveGeofence = async (geofence: GeofenceWithMetadata) => {
    try {
      // Format payload for MongoDB 2dsphere indexing logic
      const payload = {
        name: geofence.name,
        description: geofence.buildingCode,
        type: geofence.type === 'circle' ? 'radial' : 'polygon',
        coordinates: geofence.type === 'circle' 
          ? [geofence.center.longitude, geofence.center.latitude] 
          : geofence.coordinates.map(c => [c.longitude, c.latitude]), // Frontend expects to close loop in backend
        radius: geofence.type === 'circle' ? geofence.radiusMeters : null,
      };

      const { data } = await apiClient.post('/geofences', payload);
      
      // Add inserted ID to UI state
      const savedGeofence = { ...geofence, id: data.geofence_id };
      setGeofences((prev) => [...prev, savedGeofence]);
      toast.success('Spatial boundary established');
    } catch (error) {
      toast.error('Failed to save boundary rules');
    }
  };

  const handleDeleteGeofence = async (geofenceId: string) => {
    // Implement delete logic when router is ready
    toast.info('Deactivation pipeline not yet active');
  };

  if (loading) return <div className="h-screen flex items-center justify-center">Loading spatial engine...</div>;

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <Button onClick={onBack} variant="ghost" size="sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Geofence Management</h1>
          <p className="text-slate-600 text-sm mt-1">
            Create circular and polygonal geofences for attendance verification
          </p>
        </div>
      </div>
      <div className="flex-1 overflow-hidden">
        <GeofenceMap
          geofences={geofences}
          onSave={handleSaveGeofence}
          onDelete={handleDeleteGeofence}
        />
      </div>
    </div>
  );
};