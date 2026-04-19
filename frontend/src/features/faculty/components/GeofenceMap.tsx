import React, { useCallback, useState, useRef, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  Circle,
  Polygon,
  Popup,
  Marker,
  useMapEvents,
} from 'react-leaflet';
import { Trash2, Save, Plus } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import type { GeofenceWithMetadata, CircularGeofence, PolygonGeofence } from '@/types/faculty';
import { toast } from 'sonner';
import L from 'leaflet';

// --- Vite / Leaflet Icon Fix ---
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Delete the broken default icon configurations
delete (L.Icon.Default.prototype as any)._getIconUrl;
// Re-map to the statically imported Vite assets
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});
// -------------------------------
// Type guards
const isCircleGeofence = (geofence: GeofenceWithMetadata): geofence is GeofenceWithMetadata & { type: 'circle'; center: any; radiusMeters: number } => {
  return 'type' in geofence && geofence.type === 'circle';
};

const isPolygonGeofence = (geofence: GeofenceWithMetadata): geofence is GeofenceWithMetadata & { type: 'polygon'; coordinates: any[] } => {
  return 'type' in geofence && geofence.type === 'polygon';
};
interface GeofenceMapProps {
  geofences: GeofenceWithMetadata[];
  onSave: (geofence: GeofenceWithMetadata) => void;
  onDelete: (geofenceId: string) => void;
}

interface DrawingState {
  isDrawing: boolean;
  mode: 'circle' | 'polygon' | null;
  points: Array<[number, number]>;
  centerPoint: [number, number] | null;
  radiusMeters: number;
}

// Map event handler component
const MapController: React.FC<{
  onLocationClick: (latlng: L.LatLng) => void;
  drawingMode: 'circle' | 'polygon' | null;
}> = ({ onLocationClick, drawingMode }) => {
  useMapEvents({
    click: (e) => {
      if (drawingMode) {
        onLocationClick(e.latlng);
      }
    },
  });

  return null;
};

export const GeofenceMap: React.FC<GeofenceMapProps> = ({
  geofences,
  onSave,
  onDelete,
}) => {
  const [drawing, setDrawing] = useState<DrawingState>({
    isDrawing: false,
    mode: null,
    points: [],
    centerPoint: null,
    radiusMeters: 100,
  });

  const [name, setName] = useState('');
  const [buildingCode, setBuildingCode] = useState('');
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);
  
  const mapRef = useRef<L.Map>(null);

  // Fallback center if GPS is denied
  const fallbackCenter: [number, number] = [28.5355, 77.3910]; // Defaulting to Noida area

  // Request high-accuracy GPS location on component mount
  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const coords: [number, number] = [position.coords.latitude, position.coords.longitude];
          setUserLocation(coords);
          // Auto-pan the map to the user's actual location
          if (mapRef.current) {
            mapRef.current.flyTo(coords, 17, { duration: 1.5 });
          }
        },
        (error) => {
          console.warn("GPS Location denied or unavailable:", error.message);
          toast.warning("Could not access live GPS. Using default map center.");
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    }
  }, []);

  const handleStartCircle = () => {
    setDrawing({
      isDrawing: true,
      mode: 'circle',
      points: [],
      centerPoint: null,
      radiusMeters: 100,
    });
  };

  const handleStartPolygon = () => {
    setDrawing({
      isDrawing: true,
      mode: 'polygon',
      points: [],
      centerPoint: null,
      radiusMeters: 100,
    });
  };

  const handleMapClick = useCallback((latlng: L.LatLng) => {
    if (!drawing.isDrawing) return;

    if (drawing.mode === 'circle') {
      setDrawing((prev) => ({
        ...prev,
        centerPoint: [latlng.lat, latlng.lng],
      }));
    } else if (drawing.mode === 'polygon') {
      setDrawing((prev) => ({
        ...prev,
        points: [...prev.points, [latlng.lat, latlng.lng]],
      }));
    }
  }, [drawing]);

  const handleSaveGeofence = () => {
    if (!name.trim()) {
      toast.error('Please enter a geofence name');
      return;
    }

    let newGeofence: GeofenceWithMetadata;

    if (drawing.mode === 'circle' && drawing.centerPoint) {
      const circle: CircularGeofence = {
        type: 'circle',
        center: {
          latitude: drawing.centerPoint[0],
          longitude: drawing.centerPoint[1],
        },
        radiusMeters: drawing.radiusMeters,
      };

      newGeofence = {
        ...circle,
        id: `geofence-${Date.now()}`,
        name,
        buildingCode,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
    } else if (drawing.mode === 'polygon' && drawing.points.length >= 3) {
      const polygon: PolygonGeofence = {
        type: 'polygon',
        coordinates: drawing.points.map(([lat, lng]) => ({
          latitude: lat,
          longitude: lng,
        })),
      };

      newGeofence = {
        ...polygon,
        id: `geofence-${Date.now()}`,
        name,
        buildingCode,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
    } else {
      toast.error(drawing.mode === 'polygon' ? 'Polygon requires at least 3 points' : 'Please draw on the map first');
      return;
    }

    onSave(newGeofence);

    // Reset form
    setName('');
    setBuildingCode('');
    setDrawing({
      isDrawing: false,
      mode: null,
      points: [],
      centerPoint: null,
      radiusMeters: 100,
    });
  };

  const handleCancel = () => {
    setDrawing({
      isDrawing: false,
      mode: null,
      points: [],
      centerPoint: null,
      radiusMeters: 100,
    });
  };

  return (
    <div className="flex h-screen gap-4 bg-slate-50 p-4">
      {/* Map Container */}
      <div className="flex-1 flex flex-col">
        <h2 className="text-xl font-bold text-slate-900 mb-3">Geofence Management Map</h2>
        <div className="flex-1 rounded-lg overflow-hidden border border-slate-200 shadow-sm z-0">
          <MapContainer
            center={fallbackCenter}
            zoom={15}
            style={{ height: '100%', width: '100%' }}
            ref={mapRef}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
            />

            {/* User Live Location Marker */}
            {userLocation && (
              <Marker position={userLocation}>
                <Popup>Your Current Location</Popup>
              </Marker>
            )}

            {/* Render all saved geofences */}
            {geofences.map((geofence) => (
              <React.Fragment key={geofence.id}>
                {isCircleGeofence(geofence) && (
                  <Circle
                    center={[geofence.center.latitude, geofence.center.longitude]}
                    radius={geofence.radiusMeters}
                    pathOptions={{
                      color: '#4f46e5',
                      fillColor: '#4f46e5',
                      fillOpacity: 0.2,
                      weight: 2,
                    }}
                  >
                    <Popup>
                      <div className="text-sm">
                        <p className="font-semibold">{geofence.name}</p>
                        {geofence.buildingCode && (
                          <p className="text-slate-600">{geofence.buildingCode}</p>
                        )}
                        <p className="text-xs text-slate-500">
                          Radius: {geofence.radiusMeters}m
                        </p>
                      </div>
                    </Popup>
                  </Circle>
                )}

                {isPolygonGeofence(geofence) && (
                  <Polygon
                    positions={geofence.coordinates.map((c) => [c.latitude, c.longitude])}
                    pathOptions={{
                      color: '#7c3aed',
                      fillColor: '#7c3aed',
                      fillOpacity: 0.2,
                      weight: 2,
                    }}
                  >
                    <Popup>
                      <div className="text-sm">
                        <p className="font-semibold">{geofence.name}</p>
                        {geofence.buildingCode && (
                          <p className="text-slate-600">{geofence.buildingCode}</p>
                        )}
                      </div>
                    </Popup>
                  </Polygon>
                )}
              </React.Fragment>
            ))}

            {/* Live drawing preview */}
            {drawing.mode === 'circle' && drawing.centerPoint && (
              <Circle
                center={[drawing.centerPoint[0], drawing.centerPoint[1]]}
                radius={drawing.radiusMeters}
                pathOptions={{
                  color: '#f59e0b',
                  fillColor: '#f59e0b',
                  fillOpacity: 0.1,
                  weight: 2,
                  dashArray: '5, 5',
                }}
              />
            )}

            {drawing.mode === 'polygon' && drawing.points.length > 0 && (
              <Polygon
                positions={drawing.points.map(([lat, lng]) => [lat, lng])}
                pathOptions={{
                  color: '#f59e0b',
                  fillColor: '#f59e0b',
                  fillOpacity: 0.1,
                  weight: 2,
                  dashArray: '5, 5',
                }}
              />
            )}

            <MapController onLocationClick={handleMapClick} drawingMode={drawing.mode} />
          </MapContainer>
        </div>
      </div>

      {/* Control Sidebar */}
      <div className="w-80 bg-white rounded-lg border border-slate-200 shadow-sm p-6 flex flex-col">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Create Geofence</h3>

        {!drawing.isDrawing ? (
          <div className="space-y-3">
            <Button
              onClick={handleStartCircle}
              className="w-full"
              variant="outline"
            >
              <Plus className="w-4 h-4 mr-2" />
              Draw Circle
            </Button>
            <Button
              onClick={handleStartPolygon}
              className="w-full"
              variant="outline"
            >
              <Plus className="w-4 h-4 mr-2" />
              Draw Polygon
            </Button>
          </div>
        ) : (
          <div className="space-y-4 flex-1">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Geofence Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Engineering Hall"
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Building Code (optional)
              </label>
              <input
                type="text"
                value={buildingCode}
                onChange={(e) => setBuildingCode(e.target.value)}
                placeholder="e.g., ENG-101"
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {drawing.mode === 'circle' && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Radius (meters)
                </label>
                <input
                  type="number"
                  value={drawing.radiusMeters}
                  onChange={(e) =>
                    setDrawing((prev) => ({
                      ...prev,
                      radiusMeters: parseInt(e.target.value) || 100,
                    }))
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            )}

            {drawing.mode === 'polygon' && (
              <p className="text-sm text-slate-600">
                Points added: {drawing.points.length}
                {drawing.points.length < 3 && ' (need at least 3)'}
              </p>
            )}

            <div className="flex gap-2 mt-auto">
              <Button
                onClick={handleSaveGeofence}
                variant="default"
                className="flex-1"
              >
                <Save className="w-4 h-4 mr-2" />
                Save
              </Button>
              <Button
                onClick={handleCancel}
                variant="outline"
                className="flex-1"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Saved Geofences List */}
        <div className="mt-6 pt-6 border-t border-slate-200">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">Saved Geofences</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {geofences.map((geofence) => (
              <div
                key={geofence.id}
                className="flex items-center justify-between p-2 bg-slate-50 rounded border border-slate-200 text-sm"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 truncate">{geofence.name}</p>
                  <p className="text-xs text-slate-500">
                    {isCircleGeofence(geofence) ? '● Circle' : '⬠ Polygon'}
                  </p>
                </div>
                <button
                  onClick={() => onDelete(geofence.id)}
                  className="ml-2 p-1 hover:bg-red-50 rounded transition-colors"
                  title="Delete geofence"
                >
                  <Trash2 className="w-4 h-4 text-red-600" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
