import React, { type ReactNode } from 'react';
import { X } from 'lucide-react';

interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  height?: 'small' | 'medium' | 'large' | 'full';
  className?: string;
}

const heightClasses = {
  small: 'h-[40vh]',
  medium: 'h-[60vh]',
  large: 'h-[80vh]',
  full: 'h-[95vh]',
};

export const BottomSheet: React.FC<BottomSheetProps> = ({
  isOpen,
  onClose,
  title,
  children,
  height = 'medium',
  className,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col">
      {/* Backdrop */}
      <div
        className="flex-1 bg-black/40 transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Bottom Sheet */}
      <div
        className={`${heightClasses[height]} flex flex-col rounded-t-2xl bg-white shadow-2xl transition-transform duration-300 ease-out ${className}`}
      >
        {/* Header */}
        <div className={`flex items-center justify-between border-b px-6 py-4 ${className?.includes('bg-slate-950') ? 'border-slate-800' : 'border-slate-200'}`}>
          {title && <h2 className={`text-xl font-semibold ${className?.includes('bg-slate-950') ? 'text-white' : 'text-slate-900'}`}>{title}</h2>}
          <button
            onClick={onClose}
            className={`ml-auto flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${className?.includes('bg-slate-950') ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-600'}`}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {children}
        </div>
      </div>
    </div>
  );
};
