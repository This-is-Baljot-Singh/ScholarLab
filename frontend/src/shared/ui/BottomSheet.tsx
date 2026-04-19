import React, { type ReactNode } from 'react';
import { X } from 'lucide-react';

interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  height?: 'small' | 'medium' | 'large' | 'full';
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
        className={`${heightClasses[height]} flex flex-col rounded-t-2xl bg-white shadow-2xl transition-transform duration-300 ease-out`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          {title && <h2 className="text-xl font-semibold text-slate-900">{title}</h2>}
          <button
            onClick={onClose}
            className="ml-auto flex h-10 w-10 items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="h-5 w-5 text-slate-600" />
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
