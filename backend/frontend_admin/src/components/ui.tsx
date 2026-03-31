import React, { type ReactNode } from 'react';
import { X, Info, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

// Card
export const Card: React.FC<{ children: ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`bg-white shadow-sm border border-gray-200 rounded-xl overflow-hidden ${className}`}>{children}</div>
);

// Avatar
export const Avatar: React.FC<{ src?: string; fallback?: string; size?: 'sm' | 'md' | 'lg' | 'xl' }> = ({ src, fallback, size = 'md' }) => {
  const sizeClasses = { sm: 'h-8 w-8 text-xs', md: 'h-10 w-10 text-sm', lg: 'h-12 w-12 text-base', xl: 'h-16 w-16 text-lg' };
  return (
    <div className={`relative rounded-full flex items-center justify-center bg-gray-100 border border-gray-200 overflow-hidden ${sizeClasses[size]}`}>
      {src ? <img src={src} className="object-cover w-full h-full" alt="Avatar" /> : <span className="font-medium text-gray-600">{fallback}</span>}
    </div>
  );
};

// Badge
export const Badge: React.FC<{ children: ReactNode; color?: 'neutral' | 'success' | 'error' | 'warning' | 'primary'; size?: 'md' | 'lg' }> = ({ children, color = 'neutral', size = 'md' }) => {
  const colorClasses = {
    neutral: 'bg-gray-100 text-gray-700',
    success: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
    warning: 'bg-yellow-100 text-yellow-800',
    primary: 'bg-indigo-100 text-indigo-700'
  };
  const sizeClasses = { md: 'px-2 py-0.5 text-xs', lg: 'px-3 py-1 text-sm' };
  return <span className={`inline-flex items-center font-medium rounded-full ${colorClasses[color]} ${sizeClasses[size]}`}>{children}</span>;
};

// Button
export const Button: React.FC<{ children: ReactNode; variant?: 'primary' | 'secondary' | 'tertiary'; color?: 'primary' | 'error'; size?: 'sm' | 'md' | 'lg'; onClick?: () => void; disabled?: boolean; isLoading?: boolean; className?: string }> = ({ children, variant = 'primary', color = 'primary', size = 'md', onClick, disabled, isLoading, className = '' }) => {
  const baseClasses = "inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";
  
  let varClasses = '';
  if (variant === 'primary' && color === 'primary') varClasses = 'bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-500';
  if (variant === 'primary' && color === 'error') varClasses = 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500';
  if (variant === 'secondary') varClasses = 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-indigo-500';
  if (variant === 'tertiary') varClasses = 'bg-transparent text-gray-600 hover:bg-gray-100 focus:ring-gray-500';

  const sizeClasses = { sm: 'px-3 py-1.5 text-sm', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-base' };

  return (
    <button onClick={onClick} disabled={disabled || isLoading} className={`${baseClasses} ${varClasses} ${sizeClasses[size]} ${className}`}>
      {isLoading ? <span className="mr-2 animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" /> : null}
      {children}
    </button>
  );
};

// Alert
export const Alert: React.FC<{ children: ReactNode; title?: string; color?: 'success' | 'error' | 'warning' | 'info' }> = ({ children, title, color = 'info' }) => {
  const colorConfig = {
    success: { bg: 'bg-green-50', text: 'text-green-800', icon: <CheckCircle className="h-5 w-5 text-green-400" /> },
    error: { bg: 'bg-red-50', text: 'text-red-800', icon: <XCircle className="h-5 w-5 text-red-400" /> },
    warning: { bg: 'bg-yellow-50', text: 'text-yellow-800', icon: <AlertTriangle className="h-5 w-5 text-yellow-400" /> },
    info: { bg: 'bg-blue-50', text: 'text-blue-800', icon: <Info className="h-5 w-5 text-blue-400" /> }
  };
  const conf = colorConfig[color];
  return (
    <div className={`rounded-xl p-4 ${conf.bg}`}>
      <div className="flex">
        <div className="flex-shrink-0">{conf.icon}</div>
        <div className="ml-3">
          {title && <h3 className={`text-sm font-medium ${conf.text}`}>{title}</h3>}
          <div className={`text-sm ${title ? 'mt-2' : ''} ${conf.text}`}>{children}</div>
        </div>
      </div>
    </div>
  );
};

// Modal
export const Modal: React.FC<{ isOpen: boolean; onClose: () => void; title: string; children: ReactNode }> = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm transition-opacity" onClick={onClose} />
      <div className="bg-white rounded-2xl shadow-xl z-10 w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex justify-between items-center p-6 border-b border-gray-100">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-500 focus:outline-none rounded-full p-1 hover:bg-gray-100 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-6 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
};

// Tooltip
export const Tooltip: React.FC<{ children: ReactNode; content: string }> = ({ children, content }) => (
  <div className="group relative inline-block">
    {children}
    <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-md whitespace-nowrap z-50">
      {content}
      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
    </div>
  </div>
);
