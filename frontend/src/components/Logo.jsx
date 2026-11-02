import React from 'react';

export function Logo({ size = 40, className = "" }) {
  return (
    <div
      className={`pulse-logo-container ${className}`}
      style={{
        width: size,
        height: size,
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: '100%' }}
      >
        {/* Dynamic Background Ring */}
        <circle cx="50" cy="50" r="48" stroke="url(#logo-grad-1)" strokeWidth="4" strokeDasharray="10 5" opacity="0.3" />

        {/* Inner Glow Circle */}
        <circle cx="50" cy="50" r="40" fill="url(#logo-grad-2)" opacity="0.1" />

        {/* The "P" Mark / Pulse Wave Combination */}
        <path
          d="M30 70V30H50C61 30 70 39 70 50C70 61 61 70 50 70H30Z"
          stroke="white"
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Pulse Line through the center */}
        <path
          d="M25 50H35L42 35L52 65L60 45L65 50H75"
          stroke="#38bdf8"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="logo-pulse-path"
        />

        <defs>
          <linearGradient id="logo-grad-1" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
            <stop stopColor="#0ea5e9" />
            <stop offset="1" stopColor="#6366f1" />
          </linearGradient>
          <linearGradient id="logo-grad-2" x1="50" y1="10" x2="50" y2="90" gradientUnits="userSpaceOnUse">
            <stop stopColor="#0ea5e9" />
            <stop offset="1" stopColor="#312e81" />
          </linearGradient>
        </defs>
      </svg>

      <style>
        {`
          .logo-pulse-path {
            stroke-dasharray: 100;
            stroke-dashoffset: 100;
            animation: logo-pulse 3s linear infinite;
          }
          @keyframes logo-pulse {
            0% { stroke-dashoffset: 100; opacity: 0.3; }
            20% { opacity: 1; }
            50% { stroke-dashoffset: 0; }
            80% { opacity: 1; }
            100% { stroke-dashoffset: -100; opacity: 0.3; }
          }
        `}
      </style>
    </div>
  );
}
