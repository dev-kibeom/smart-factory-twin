'use client';

import {
  CategoryScale,
  ChartData,
  Chart as ChartJS,
  ChartOptions,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip
} from 'chart.js';
import React, { useEffect, useRef, useState } from 'react';
import { Line } from 'react-chartjs-2';

// ChartJS 플러그인 레지스터 무결성 안착 [cite: 677]
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

export const OeeChart: React.FC = () => {
  // 웹소켓 인스턴스의 상호 참조 및 중복 생성을 원천 차단하기 위한 레퍼런스 가드
  const wsRef = useRef<WebSocket | null>(null);

  const [chartData, setChartData] = useState<ChartData<'line'>>({
    labels: [],
    datasets: [
      {
        label: 'Overall OEE (%)',
        data: [],
        borderColor: 'rgb(56, 189, 248)',
        backgroundColor: 'rgba(56, 189, 248, 0.1)',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.2,
      },
      {
        label: 'Availability Index (%)',
        data: [],
        borderColor: 'rgb(34, 197, 94)',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.1,
      },
      {
        label: 'Performance Index (%)',
        data: [],
        borderColor: 'rgb(234, 179, 8)',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.1,
      }
    ],
  });

  useEffect(() => {
    // [인수인계서 3-3 / 4] WebRTC 시그널링 관문과 동일한 소켓 허브 링크 개통 [cite: 385, 680]
    const metricsWs = new WebSocket('ws://localhost:8000/api/v1/signal/ws/web_chart_console');
    wsRef.current = metricsWs;

    metricsWs.onopen = () => {
      console.log('📊 [Next.js OeeChart] ISA-95 Level 3 고주파 데이터 파이프라인 수전 개통.');
    };

    metricsWs.onmessage = (event) => {
      try {
        const rawPacket = JSON.parse(event.data);
        
        // factory_oee_metrics 스키마 패킷 판정 가드레일 (일반 SDP/ICE Candidate 패킷 쓰루 처리) [cite: 681]
        if (rawPacket.measurement !== 'factory_oee_metrics' || typeof rawPacket.overall_oee !== 'number') {
          return; 
        }

        const nowStr = new Date().toLocaleTimeString('ko-KR', { 
          hour12: false, 
          hour: '2-digit', 
          minute: '2-digit', 
          second: '2-digit' 
        });

        setChartData((prevData) => {
          const nextLabels = [...prevData.labels, nowStr];
          
          // 백엔드 정합 수식 모델 사양(A, P, Q 및 OEE % 스케일) 데이터 이식
          const nextOee = [...(prevData.datasets[0].data as number[]), rawPacket.overall_oee];
          const nextAvail = [...(prevData.datasets[1].data as number[]), rawPacket.availability_index * 100];
          const nextPerf = [...(prevData.datasets[2].data as number[]), rawPacket.performance_index * 100];

          // [핵심 자원 제어]: 10Hz 초고속 적재 시 브라우저 메모리 폭발 방어용 윈도우 600개 FIFO 제한 
          if (nextLabels.length > 600) {
            nextLabels.shift();
            nextOee.shift();
            nextAvail.shift();
            nextPerf.shift();
          }

          return {
            ...prevData,
            labels: nextLabels,
            datasets: [
              { ...prevData.datasets[0], data: nextOee },
              { ...prevData.datasets[1], data: nextAvail },
              { ...prevData.datasets[2], data: nextPerf },
            ],
          };
        });
      } catch (err) {
        // 고속 스트림 데이터 파싱 노이즈 예외 무시 [cite: 686]
      }
    };

    metricsWs.onerror = (error) => {
      console.error('📊 [OeeChart] 시계열 수전 관문 통신 결함:', error);
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false, // 10Hz 초고속 갱신 시 차트 자체 렌더링 애니메이션 부하 소거 (최적화 핵심)
    plugins: {
      legend: {
        position: 'top' as const,
        labels: { color: '#94a3b8', font: { family: 'monospace', size: 11 } },
      },
      tooltip: {
        enabled: true,
        mode: 'index',
        intersect: false,
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { maxTicksLimit: 8, color: '#64748b', font: { size: 9, family: 'monospace' } },
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: '#1e293b' },
        ticks: { color: '#64748b', font: { size: 10, family: 'monospace' } },
      },
    },
  };

  return (
    <div className="w-full h-[350px] bg-slate-950 p-5 rounded-xl border border-slate-800 shadow-2xl">
      <div className="mb-2">
        <h3 className="text-sm font-bold font-mono text-slate-200">ISA-95 Level 3 — Real-time Factory OEE Stream Chart [cite: 690]</h3>
        <p className="text-xs font-mono text-slate-500">10Hz High-frequency Telemetry Data via InfluxDB TSDB Engine [cite: 690]</p>
      </div>
      <div className="w-full h-[260px]">
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
};

export default OeeChart;