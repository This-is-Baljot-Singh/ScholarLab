import React from 'react';
import { FileText, Zap, PieChart, BookOpen } from 'lucide-react';
import type { CurriculumItem } from '@/types/student';

interface CurriculumGridProps {
  items: CurriculumItem[];
  onItemClick: (item: CurriculumItem) => void;
}

const getIconForType = (type: string) => {
  switch (type) {
    case 'pdf':
      return <FileText className="h-6 w-6" />;
    case 'quiz':
      return <PieChart className="h-6 w-6" />;
    case 'video':
      return <BookOpen className="h-6 w-6" />;
    default:
      return <Zap className="h-6 w-6" />;
  }
};

const getTypeLabel = (type: string) => {
  return type.charAt(0).toUpperCase() + type.slice(1);
};

export const CurriculumGrid: React.FC<CurriculumGridProps> = ({ items, onItemClick }) => {
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => onItemClick(item)}
          disabled={!item.isUnlocked}
          className={`flex items-center gap-4 rounded-xl p-4 transition-all duration-200 ${
            item.isUnlocked
              ? 'active:scale-95 bg-white shadow-sm hover:shadow-md'
              : 'bg-slate-100 opacity-50'
          }`}
        >
          {/* Icon with animation for newly unlocked items */}
          <div
            className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg ${
              item.isUnlocked
                ? 'bg-indigo-100 text-indigo-600'
                : 'bg-slate-300 text-slate-600'
            } ${item.unlockedAt ? 'animate-bounce' : ''}`}
          >
            {getIconForType(item.type)}
          </div>

          {/* Content */}
          <div className="flex-1 text-left">
            <p className="font-semibold text-slate-900">{item.title}</p>
            <p className="text-xs text-slate-500">{getTypeLabel(item.type)}</p>
            {item.metadata && item.metadata.duration && (
              <p className="text-xs text-slate-500">⏱️ {item.metadata.duration} min</p>
            )}
            {item.metadata && item.metadata.pages && (
              <p className="text-xs text-slate-500">📄 {item.metadata.pages} pages</p>
            )}
            {item.metadata && item.metadata.points && (
              <p className="text-xs text-slate-500">⭐ {item.metadata.points} points</p>
            )}
          </div>

          {/* Unlock badge */}
          {!item.isUnlocked && (
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-300">
              🔒
            </div>
          )}

          {item.isUnlocked && (
            <div className="text-indigo-600">→</div>
          )}
        </button>
      ))}
    </div>
  );
};
