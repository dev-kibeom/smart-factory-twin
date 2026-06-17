// frontend/src/hooks/useWebRtc.ts
import { useEffect, useRef, useState } from 'react';

interface UseWebRtcProps {
  signalingUrl: string;
  clientId: string;
  targetId: string;
}

// ===========================================================================
// 🛡️ [싱글톤 생명주기 가드레일 체결]
// F12 크기 변경으로 인해 컴포넌트가 백만 번 재렌더링(Re-mount)되어도,
// 전역 메모리 평면에 안착한 웹소켓과 PeerConnection 자산은 절대 죽지 않고 
// 초록불 통전 상태를 무한 유지하도록 useEffect 스코프 바깥으로 포인터를 탈출시킵니다.
// ===========================================================================
let globalWs: WebSocket | null = null;
let globalPc: RTCPeerConnection | null = null;
let globalIceQueue: RTCIceCandidateInit[] = [];

export const useWebRtc = ({ signalingUrl, clientId, targetId }: UseWebRtcProps) => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // 컴포넌트 라이프사이클 내에서 싱글톤을 안전하게 바인딩할 레퍼런스 가드 사수
  const pcRef = useRef<RTCPeerConnection | null>(null);

  useEffect(() => {
    const pcConfig: RTCConfiguration = {
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
      bundlePolicy: 'max-bundle',
    };

    // 🔌 [정격 교정] TDZ 결함을 소거하기 위해 표준 함수 선언식(Function Statement) 사양으로 전면 개전
    function initializePeerConnection() {
      // 이미 글로벌 커넥션이 PLAYING 중이면 새로 만들지 않고 재사용 인터록 [cite: 644]
      if (globalPc) {
        pcRef.current = globalPc;
        return;
      }

      const pc = new RTCPeerConnection(pcConfig);

      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          setStream(event.streams[0]);
        } else {
          const inboundStream = new MediaStream([event.track]);
          setStream(inboundStream);
        }
        setIsConnected(true);
      };

      pc.onicecandidate = (event) => {
        if (event.candidate && globalWs && globalWs.readyState === WebSocket.OPEN) {
          globalWs.send(
            JSON.stringify({
              target_id: targetId,
              type: 'candidate',
              sdpMLineIndex: event.candidate.sdpMLineIndex,
              candidate: event.candidate.candidate,
            })
          );
        }
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'connected') setIsConnected(true);
        else if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') setIsConnected(false);
      };

      globalPc = pc;
      pcRef.current = pc;
    }

    function connectSignalingServer() {
      // 이미 소켓 관문이 개통되어 생존해 있다면 중복 커넥션 생성 전면 차단 [cite: 650]
      if (globalWs && (globalWs.readyState === WebSocket.OPEN || globalWs.readyState === WebSocket.CONNECTING)) {
        if (globalWs.readyState === WebSocket.OPEN) {
          setIsConnected(globalPc?.connectionState === 'connected');
        }
        return;
      }

      const ws = new WebSocket(`${signalingUrl}/${clientId}`);
      
      ws.onopen = () => {
        console.log(`📡 [Next.js WebRTC] 싱글톤 소켓 관문 무결성 개통 완료.`);
        globalIceQueue = [];
        initializePeerConnection();
      };

      ws.onmessage = async (event) => {
        try {
          const msg = JSON.parse(event.data);
          console.log(`📥 [Next.js 수전] 패킷 인입 타입 -> ${msg.type}`);

          if (msg.type === 'offer') {
            if (!globalPc) return;
            await globalPc.setRemoteDescription(new RTCSessionDescription({ type: 'offer', sdp: msg.sdp }));

            if (globalIceQueue.length > 0) {
              await Promise.all(
                globalIceQueue.map(cand => globalPc!.addIceCandidate(new RTCIceCandidate(cand)))
              );
              globalIceQueue = [];
            }
            
            const answer = await globalPc.createAnswer();
            await globalPc.setLocalDescription(answer);

            ws.send(JSON.stringify({ target_id: targetId, type: 'answer', sdp: answer.sdp }));
          } else if (msg.type === 'candidate') {
            if (!globalPc) return;
            const candidateInit: RTCIceCandidateInit = {
              candidate: msg.candidate,
              sdpMLineIndex: msg.sdpMLineIndex,
            };
            if (!globalPc.remoteDescription) {
              globalIceQueue.push(candidateInit);
            } else {
              await globalPc.addIceCandidate(new RTCIceCandidate(candidateInit));
            }
          }
        } catch (err: any) {
          setError(err.message || 'WebRTC Signalling Handling Error');
        }
      };

      ws.onclose = () => {
        globalWs = null;
        setIsConnected(false);
        setTimeout(connectSignalingServer, 3000);
      };

      globalWs = ws;
    }

    // 초기 실행 진입점 가동
    connectSignalingServer();

    return () => {
      // 컴포넌트 언마운트 시의 소켓 파괴 인터록을 거세하여 연속 재생 무결성 보존 [cite: 664]
    };
  }, [signalingUrl, clientId, targetId]);

  return { stream, isConnected, error };
};