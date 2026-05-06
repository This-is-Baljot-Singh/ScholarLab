import { GeofenceManager } from '../components/GeofenceManager';

export const GeofencesPage = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Geofence Management</h1>
        <p className="text-slate-500 text-sm font-medium">Define and manage spatial boundaries for automated attendance.</p>
      </div>
      <GeofenceManager />
    </div>
  );
};
