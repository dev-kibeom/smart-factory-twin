import { useEffect, useRef, useState } from 'react';

interface UseWebRtcProps {
  signalingUrl: string;
  clientId: string;
  targetId: string;
}

export const useWebRtc = ({ signalingUrl, clientId, targetId }: UseWebRtcProps) => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  
  // 💡 [표준 공학적 가드레일]: 원격 명세 안착 전 인입되는 ICE Candidate 임시 격리 큐 생성
  const iceQueueRef = useRef<RTCIceCandidateInit[]>([]);

  useEffect(() => {
    // 1. WebRTC RTCConfiguration 설정 (DTLS-SRTP 보안 암호화 및 ICE 수수 규격 명시)
    const pcConfig: RTCConfiguration = {
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
      bundlePolicy: 'max-bundle',
    };

    const initializePeerConnection = () => {
      const pc = new RTCPeerConnection(pcConfig);

      // 인입되는 원격 H.264 미디어 트랙 감지 즉시 프론트엔드 미디어 스트림 파이프라인 바인딩
      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          setStream(event.streams[0]);
        } else {
          const inboundStream = new MediaStream([event.track]);
          setStream(inboundStream);
        }
        setIsConnected(true);
      };

      // 브라우저 단말 내부에서 생성된 ICE 캔디데이트를 웹소켓을 경유하여 로봇 에이전트로 전포
      pc.onicecandidate = (event) => {
        if (event.candidate && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(
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
        if (pc.connectionState === 'connected') {
          setIsConnected(true);
        } else if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
          setIsConnected(false);
        }
      };

      pcRef.current = pc;
    };

    // 2. FastAPI 시그널링 관문 웹소켓 채널 개통
    const connectSignalingServer = () => {
      const ws = new WebSocket(`${signalingUrl}/${clientId}`);

      ws.onopen = () => {
        console.log(`📡 [Next.js WebRTC] 시그널링 웹소켓 개통 완료 Client ID: ${clientId}`);
        // 새로운 연결 시 격리 큐 초기화로 자원 경합 방지
        iceQueueRef.current = [];
        initializePeerConnection();
      };

      ws.onmessage = async (event) => {
        try {
          const msg = JSON.parse(event.data);
          // 목적지가 내가 아닌 패킷은 자원 경합 방지를 위해 선제적 차단 격리
          // if (msg.target_id !== clientId) return;

          console.log(`📥 [Next.js 수전] 시그널 패킷 인입 타입 -> ${msg.type}`);

          if (msg.type === 'offer') {
            if (!pcRef.current) return;
            
            // 1) 로봇 측 GStreamer에서 생성한 SDP Offer를 원격 기술서로 락인
            await pcRef.current.setRemoteDescription(new RTCSessionDescription({ type: 'offer', sdp: msg.sdp }));
            console.log(" ✔ [Next.js WebRTC] 원격 미디어 명세(Remote Description) 안착 완료.");

            // 💡 2) [큐 소출 인터록 연격]: 오퍼가 안착했으므로, 그동안 쌓여있던 ICE 패킷을 전량 덤프 투사
            if (iceQueueRef.current.length > 0) {
              console.log(` 🚀 [격리 큐 소출] 대기 중이던 ${iceQueueRef.current.length}개의 ICE Candidate 일괄 투사 개시.`);
              await Promise.all(
                iceQueueRef.current.map(cand => pcRef.current!.addIceCandidate(new RTCIceCandidate(cand)))
              );
              iceQueueRef.current = []; // 소출 마감 청소
            }
            
            // 3) 브라우저 수신 전용 Answer 생성 및 로컬 락인 후 역방향 사출
            const answer = await pcRef.current.createAnswer();
            await pcRef.current.setLocalDescription(answer);

            ws.send(
              JSON.stringify({
                target_id: targetId,
                type: 'answer',
                sdp: answer.sdp,
              })
            );
          } else if (msg.type === 'candidate') {
            if (!pcRef.current) return;

            const candidateInit: RTCIceCandidateInit = {
              candidate: msg.candidate,
              sdpMLineIndex: msg.sdpMLineIndex,
            };

            // ===========================================================================
            // 🛡️ [표준 공학적 상태 가드레일 체결]
            // 원격 명세(Offer)가 아직 힙메모리에 적재되지 않았다면, 자바스크립트 스레드를 멈추지 않고
            // 안전하게 메모리 큐로 우회 격리 저장하여 레이스 컨디션을 무력화합니다.
            // ===========================================================================
            if (!pcRef.current.remoteDescription) {
              console.warn(" ⏳ [레이스 컨디션 포착] 원격 명세 누락 상태. ICE Candidate 임시 격리 격하 처분.");
              iceQueueRef.current.push(candidateInit);
            } else {
              // 명세가 있는 정상 상태라면 즉시 다이렉트 소켓 링킹 수행
              await pcRef.current.addIceCandidate(new RTCIceCandidate(candidateInit));
            }
          }
        } catch (err: any) {
          console.error('❌ [Next.js WebRTC 내부 패킷 처리 예외]', err);
          setError(err.message || 'WebRTC Signalling Handling Error');
        }
      };

      ws.onerror = (err) => {
        console.error('🚨 [시그널링 웹소켓 에러 발생]', err);
        setError('Signaling WebSocket connection failed.');
      };

      ws.onclose = () => {
        console.warn('🛑 [시그널링 웹소켓 끊김] 3초 후 재구동 인터록 가동.');
        setIsConnected(false);
        setTimeout(connectSignalingServer, 3000);
      };

      wsRef.current = ws;
    };

    connectSignalingServer();

    // 언마운트 시 브라우저 메모리 폭발 및 자원 경합 차단을 위한 클린 격리 디스트로이어 선언
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (pcRef.current) {
        pcRef.current.close();
        pcRef.current = null;
      }
      setStream(null);
      setIsConnected(false);
      iceQueueRef.current = [];
    };
  }, [signalingUrl, clientId, targetId]);

  return { stream, isConnected, error };
};