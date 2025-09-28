'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';

export default function HomePage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-20"></div>
      
      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 sm:px-6 lg:px-8">
        {/* Hero Section */}
        <div className="text-center mb-16">
          {/* Icon/Logo */}
          <div className="mb-8">
            <div className="inline-flex items-center justify-center w-24 h-24 bg-slate-700 rounded-full border-2 border-slate-600 shadow-2xl">
              <svg 
                className="w-12 h-12 text-slate-300" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" 
                />
              </svg>
            </div>
          </div>

          {/* Title */}
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white mb-6 tracking-tight">
            <span className="block">MP3</span>
            <span className="block bg-gradient-to-r from-slate-300 to-slate-500 bg-clip-text text-transparent">
              Stenography
            </span>
            <span className="block text-slate-400 text-3xl sm:text-4xl lg:text-5xl font-medium mt-2">
              Tool
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-xl sm:text-2xl text-slate-400 max-w-3xl mx-auto leading-relaxed">
            Securely hide and extract messages within MP3 audio files using advanced stenographic techniques
          </p>
        </div>

        {/* Navigation Buttons */}
        <div className="flex flex-col sm:flex-row gap-6 w-full max-w-md">
          {/* Encrypt Button */}
          <Link 
            href="/encrypt" 
            className="group relative flex-1 bg-slate-800 hover:bg-slate-700 border-2 border-slate-600 hover:border-slate-500 rounded-xl px-8 py-6 transition-all duration-300 transform hover:scale-105 hover:shadow-2xl"
          >
            <div className="flex flex-col items-center text-center">
              <div className="w-12 h-12 bg-slate-700 group-hover:bg-slate-600 rounded-lg flex items-center justify-center mb-4 transition-colors duration-300">
                <svg 
                  className="w-6 h-6 text-slate-300 group-hover:text-white transition-colors duration-300" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" 
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2 group-hover:text-slate-100 transition-colors duration-300">
                Encrypt
              </h3>
              <p className="text-slate-400 group-hover:text-slate-300 text-sm transition-colors duration-300">
                Hide your message within an MP3 file
              </p>
            </div>
          </Link>

          {/* Decrypt Button */}
          <Link 
            href="/decrypt" 
            className="group relative flex-1 bg-slate-800 hover:bg-slate-700 border-2 border-slate-600 hover:border-slate-500 rounded-xl px-8 py-6 transition-all duration-300 transform hover:scale-105 hover:shadow-2xl"
          >
            <div className="flex flex-col items-center text-center">
              <div className="w-12 h-12 bg-slate-700 group-hover:bg-slate-600 rounded-lg flex items-center justify-center mb-4 transition-colors duration-300">
                <svg 
                  className="w-6 h-6 text-slate-300 group-hover:text-white transition-colors duration-300" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" 
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2 group-hover:text-slate-100 transition-colors duration-300">
                Decrypt
              </h3>
              <p className="text-slate-400 group-hover:text-slate-300 text-sm transition-colors duration-300">
                Extract hidden messages from MP3 files
              </p>
            </div>
          </Link>
        </div>

        {/* Additional Info */}
        <div className="mt-16 text-center">
          <p className="text-slate-500 text-sm">
            Powered by advanced audio stenography algorithms
          </p>
        </div>
      </div>

      {/* Footer */}
      <div className="p-8 text-center">
        <p className="text-slate-600 text-xs">
          © IF4020 Kriptografi - Tucil 2 by Zaki Yudhistira Candra (13522039) and Edbert Eddyson Gunawan (13522039).
        </p>
      </div>
    </div>
  );
}
