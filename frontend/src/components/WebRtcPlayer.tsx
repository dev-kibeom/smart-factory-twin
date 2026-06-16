'use client';

import React, { useEffect, useRef } from 'react';
import { useWebRtc } from '../hooks/useWebRtc';

export const WebRtcPlayer: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  
  // 인수인계서 상 정의된 IT Gateway 주소 매핑 및 상호 참조 꼬임 격리 구조 추종
  const { stream, isConnected, error } = useWebRtc({
    signalingUrl: 'ws://localhost:8000/api/v1/signal/ws',
    clientId: 'web_ui_console',
    targetId: 'webrtc_streamer_node'
  });

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  return (
    <div className="relative w-full h-[480px] bg-slate-950 rounded-xl overflow-hidden border border-slate-800 shadow-2xl">
      {/* 초저지연 Glass-to-Glass 200ms 미만 비디오 플레이어 평면 */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={`w-full h-full object-cover transition-opacity duration-500 ${isConnected ? 'opacity-100' : 'opacity-20'}`}
      />

      {/* 상태 가시화 인디케이터 오버레이 패널 */}
      <div className="absolute top-4 left-4 flex items-center space-x-2 z-10">
        <span className={`w-3 h-3 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
        <span className="text-xs font-mono font-bold text-white uppercase bg-slate-900/80 px-2.5 py-1 rounded-md border border-slate-700/50">
          {isConnected ? 'AMR_01 P2P STREAMING ON' : 'CONNECTING OT MEDIA PLANE'}
        </span>
      </div>

      {!isConnected && !error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center space-y-3 bg-slate-950/70 backdrop-blur-sm">
          <div className="w-8 h-8 border-4 border-slate-700 border-t-sky-500 rounded-full animate-spin" />
          <p className="text-xs font-mono text-slate-400">Negotiating DTLS-SRTP Security Multi-Layer...</p>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-rose-950/40 backdrop-blur-sm px-6">
          <p className="text-xs font-mono text-rose-400 border border-rose-800/50 bg-slate-900/90 px-4 py-3 rounded-lg shadow-lg">
            🚨 [CRITICAL VIDEO SYSTEM DEGRADED]: {error}
          </p>
        </div>
      )}
    </div>
  );
};

export default WebRtcPlayer;