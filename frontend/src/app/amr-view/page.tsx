'use client';

import { useState } from 'react';
import FaultPanel from '../../components/FaultPanel'; // 신규 컴포넌트 편입 
import OeeChart from '../../components/OeeChart';
import WebRtcPlayer from '../../components/WebRtcPlayer';

export default function AmrViewDashboard() {
  const [workOrderNum, setWorkOrderNum] = useState('WO-2026-001'); // 2026년 정격 공정 수수
  const [partId, setPartId] = useState('CARGO_BOX_A'); 
  const [qty, setQty] = useState(5); 
  const [dispatchStatus, setDispatchStatus] = useState<string | null>(null); 
  const [isDispatching, setIsDispatching] = useState(false); 

  const handleDispatchProduction = async () => { 
    setIsDispatching(true); 
    setDispatchStatus(null); 
    try {
      // 1. 자산 인가 토큰 선행 발급 (Bearer 인증 인터록 해제 절차 준수) 
      const tokenRes = await fetch('http://localhost:8000/api/auth/token?equipment_id=web_ui_console', {
        method: 'POST',
      });
      const tokenData = await tokenRes.json(); 
      const jwtToken = tokenData.access_token; 

      // 2. MES 생산 오더 Dispatched 및 VDA 5050 명령 하향 송출 API 직격 타격 
      const dispatchUrl = `http://localhost:8000/api/work-orders/dispatch?work_order_number=${workOrderNum}&part_id=${partId}&quantity=${qty}`;
      const res = await fetch(dispatchUrl, { 
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${jwtToken}`, 
        },
      });
      const result = await res.json(); 
      if (res.ok) {
        setDispatchStatus(`✔ SUCCESS: ${result.status} (ID: ${result.order_id})`); 
      } else {
        setDispatchStatus(`❌ FAILURE: ${result.detail || 'API Gate Error'}`);
      }
    } catch (err: any) {
      setDispatchStatus(`❌ EXCEPTION: ${err.message}`); 
    } finally {
      setIsDispatching(false); 
    }
  };

  return ( 
    <main className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <header className="mb-8 border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-black font-mono tracking-tight text-white flex items-center space-x-3">
          <span>🧠 SMART FACTORY DIGITAL TWIN SYSTEM CONTROL CONSOLE </span>
        </h1>
        <p className="text-xs font-mono text-slate-400 mt-1">
          Sim-to-Real Multi-Agent Edge Control and Real-time Telemetry Verification Environment
        </p>
      </header>

      {/* 3대 엔지니어링 도메인 + 디버그 평면 분산 레이아웃 매핑 */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        
        {/* 좌측 평면: 생산 제어 및 고장 주입 컨트롤 타워 섹션 */}
        <div className="flex flex-col space-y-8">
          {/* MES 작업지시 컴포넌트 */}
          <div className="bg-slate-950 border border-slate-800 p-6 rounded-xl shadow-xl flex flex-col space-y-4">
            <div>
              <h2 className="text-sm font-bold font-mono text-sky-400">Carbon MES Production Command Panel</h2>
              <p className="text-xs font-mono text-slate-500">ACID Transaction Scheduling & VDA 5050 Downlink</p>
            </div>
            <hr className="border-slate-800" />
            
            <div className="space-y-3 font-mono text-xs">
              <div className="flex flex-col space-y-1">
                <label className="text-slate-400">WORK ORDER NUMBER</label>
                <input 
                  type="text" 
                  value={workOrderNum} 
                  onChange={(e) => setWorkOrderNum(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex flex-col space-y-1">
                <label className="text-slate-400">TARGET MATERIAL ID</label>
                <input 
                  type="text" 
                  value={partId} 
                  onChange={(e) => setPartId(e.target.value)} 
                  className="bg-slate-900 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex flex-col space-y-1">
                <label className="text-slate-400">DISPATCH QUANTITY (EA)</label>
                <input 
                  type="number" 
                  value={qty} 
                  onChange={(e) => setQty(Number(e.target.value))} 
                  className="bg-slate-900 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <button
              onClick={handleDispatchProduction}
              disabled={isDispatching}
              className="w-full bg-sky-600 hover:bg-sky-500 text-white font-mono font-bold text-xs py-3 rounded-lg transition shadow-md disabled:bg-slate-800 disabled:text-slate-500"
            >
              {isDispatching ? 'DISPATCHING TO OT AGENTS...' : '⚡ ORDER DISPATCH (VDA 5050)'}
            </button>

            {dispatchStatus && (
              <div className="bg-slate-900 border border-slate-800 p-3 rounded text-[11px] font-mono whitespace-pre-wrap leading-relaxed text-slate-300">
                {dispatchStatus}
              </div>
            )}
          </div>

          {/* 고장 주입 원격 진단 인터페이스 결합 */}
          <FaultPanel />
        </div>

        {/* 우측 평면: 고대역폭 미디어 스트림 및 데이터 뷰포트 배치 (2개 열 점유) */}
        <div className="xl:col-span-2 space-y-8">
          <div>
            <WebRtcPlayer /> 
          </div>
          <div>
            <OeeChart />
          </div>
        </div>

      </div>
    </main>
  );
}