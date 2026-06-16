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
import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

export const OeeChart: React.FC = () => {
  // 브라우저 힙 크래시 방어용 FIFO 데이터 버퍼 스냅샷 구조화 선언
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
        label: 'Availability Index',
        data: [],
        borderColor: 'rgb(34, 197, 94)',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.1,
      },
      {
        label: 'Performance Index',
        data: [],
        borderColor: 'rgb(234, 179, 8)',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.1,
      }
    ],
  });

  useEffect(() => {
    // 💡 실전 검증 설계: 10Hz OEE 시계열 전포 패킷 수전을 위해 백엔드 웹소켓 세션 링킹 개통
    // 실제 운영 상황에서는 InfluxDB 데이터를 백엔드가 가공하여 웹소켓으로 프론트에 스트리밍하는 규격을 추종
    const metricsWs = new WebSocket('ws://localhost:8000/api/v1/signal/ws/web_chart_console');

    metricsWs.onmessage = (event) => {
      try {
        const rawPacket = JSON.parse(event.data);
        
        // factory_oee_metrics 스키마 패킷 판정 가드레일 수립
        if (rawPacket.measurement !== 'factory_oee_metrics' && !rawPacket.overall_oee) {
          // 만약 일반 시그널링 SDP 패킷이 인입될 경우 쓰루 처리하여 상호 참조 간섭 차단
          return; 
        }

        const nowStr = new Date().toLocaleTimeString('ko-KR', { hour12: false });

        setChartData((prevData) => {
          const nextLabels = [...prevData.labels, nowStr];
          const nextOee = [...(prevData.datasets[0].data as number[]), rawPacket.overall_oee];
          const nextAvail = [...(prevData.datasets[1].data as number[]), rawPacket.availability_index * 100];
          const nextPerf = [...(prevData.datasets[2].data as number[]), rawPacket.performance_index * 100];

          // [핵심 자원 제어 아키텍처 규칙]: 최대 윈도우 크기 600개 스냅샷 초과 시 FIFO 시프팅
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
        // 고속 파싱 스트림 예외 무시
      }
    };

    return () => {
      metricsWs.close();
    };
  }, []);

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: { color: '#94a3b8', font: { family: 'monospace', size: 11 } },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { maxTicksLimit: 10, color: '#64748b', font: { size: 9 } },
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: '#1e293b' },
        ticks: { color: '#64748b', font: { size: 10 } },
      },
    },
  };

  return (
    <div className="w-full h-[350px] bg-slate-950 p-5 rounded-xl border border-slate-800 shadow-2xl">
      <div className="mb-2">
        <h3 className="text-sm font-bold font-mono text-slate-200">ISA-95 Level 3 — Real-time Factory OEE Stream Chart</h3>
        <p className="text-xs font-mono text-slate-500">10Hz High-frequency Telemetry Data via InfluxDB TSDB Engine</p>
      </div>
      <div className="w-full h-[260px]">
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
};

export default OeeChart;