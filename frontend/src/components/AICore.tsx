/**
 * AICore component: A visual representation of the AI's state.
 * Renders a dynamic, animated orb that reacts to volume and active states.
 */
"use client";

import React from 'react';

export default function AICore({ isActive = false, size = 165, volume = 0 }) {
  // Volume ranges from 0 to 1
  const isSpeaking = volume > 0.15;
  const scale = 1 + (isSpeaking ? volume * 0.4 : 0);
  
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      {/* Energy Glow - 3/4 Radius */}
      <div 
        className={`absolute rounded-full blur-[40px] transition-all duration-1000 ease-in-out ${isActive ? 'opacity-30' : 'opacity-0'}`}
        style={{ 
          width: size * 1.2,
          height: size * 1.2,
          background: 'radial-gradient(circle, rgba(34,211,238,0.3) 0%, rgba(99,102,241,0.1) 50%, transparent 100%)',
          transform: `scale(${isSpeaking ? 1.2 + volume : 1})`,
        }}
      />

      {/* Main Core Container */}
      <div 
        className={`relative w-full h-full flex items-center justify-center transition-all duration-700 ease-out`}
        style={{ transform: `scale(${scale})` }}
      >
        
        {/* Layer 1: The Emerald/Cyan Flow (Outer) */}
        <div 
          className={`absolute w-full h-full rounded-full bg-gradient-to-tr from-cyan-500/30 via-emerald-400/20 to-transparent blur-xl transition-all duration-1000 ${isSpeaking ? 'animate-[fast_0.3s_linear_infinite]' : 'animate-[slow_25s_linear_infinite]'}`}
          style={{ 
            borderRadius: isSpeaking ? '30% 70% 70% 30% / 30% 30% 70% 70%' : '50%',
            boxShadow: isSpeaking ? `0 0 ${40 + volume * 100}px rgba(34, 211, 238, 0.4)` : 'none'
          }}
        />

        {/* Layer 2: The Indigo/Violet Flow (Middle) */}
        <div 
          className={`absolute w-4/5 h-4/5 rounded-full bg-gradient-to-bl from-indigo-600/40 via-violet-500/20 to-transparent blur-lg transition-all duration-1000 ${isSpeaking ? 'animate-[fast_0.5s_linear_infinite_reverse]' : 'animate-[slow_40s_linear_infinite_reverse]'}`}
          style={{ 
            borderRadius: isSpeaking ? '70% 30% 30% 70% / 70% 70% 30% 30%' : '50%',
          }}
        />

        {/* Layer 3: Crystal Core (The "Eye") */}
        <div 
          className={`relative z-10 w-1/3 h-1/3 bg-white rounded-full transition-all duration-150 ease-out border border-cyan-200/50`}
          style={{ 
            boxShadow: `0 0 ${isSpeaking ? 40 + volume * 120 : 20}px rgba(34, 211, 238, ${0.6 + volume})`,
            transform: isSpeaking ? `scale(${1 + volume * 0.3})` : 'scale(1)'
          }}
        >
          {/* Inner Glowing Center - Cyan Core */}
          <div className="absolute inset-0.5 bg-gradient-to-br from-white via-cyan-100 to-blue-200 rounded-full overflow-hidden">
             {/* Small rotating dot inside */}
             <div className="absolute top-1/4 left-1/4 w-1/2 h-1/2 bg-cyan-400/20 rounded-full animate-spin" style={{ animationDuration: '2s' }} />
          </div>
          
          {/* High speed pulse on volume */}
          {isSpeaking && (
            <div className="absolute inset-0 bg-cyan-400/30 rounded-full animate-ping" style={{ animationDuration: '0.3s' }} />
          )}
        </div>
      </div>

      {/* Floating Particles / Orbital Rings */}
      {isActive && (
        <div 
          className={`absolute inset-[-40px] border border-cyan-500/5 rounded-full ${isSpeaking ? 'animate-[spin_4s_linear_infinite]' : 'animate-[slow_60s_linear_infinite]'}`}
        />
      )}

      <style jsx>{`
        @keyframes slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes fast {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
