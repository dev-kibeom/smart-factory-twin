'use client';

import React, { useState } from 'react';

export const FaultPanel: React.FC = () => {
  const [targetComponent, setTargetComponent] = useState<string>('amr_01_lidar');
  const [faultCode, setFaultCode] = useState<number>(401);
  const [intensity, setIntensity] = useState<number>(0.8);
  const [injectionStatus, setInjectionStatus] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleInjectFault = async () => {
    setIsLoading(true);
    setInjectionStatus(null);
    try {
      // [Task 4-1 / FRS-07.1] 프로그래머틱 고장 주입 API 직격 호출 [cite: 199, 315]
      const response = await fetch(`http://localhost:8000/api/v1/components/${targetComponent}/faults`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fault_code: Number(faultCode),
          intensity: Number(intensity), // [핫픽스 수복] float 구문을 Number 정격 규격으로 교정
        }),
      });

      const result = await response.json();
      if (response.ok) {
        setInjectionStatus(
          `⚠️ [주입 성공] Code: ${result.fault_code}\n` +
          `강도: ${result.current_intensity}\n` +
          `영향: ${result.impact_on_oee}`
        );
      } else {
        setInjectionStatus(`❌ 실패: ${result.detail || 'API 내부 결함'}`);
      }
    } catch (err: any) {
      setInjectionStatus(`❌ 통신 예외 발생: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearFault = async () => {
    setIsLoading(true);
    setInjectionStatus(null);
    try {
      // 고장 강도 0.0을 인가하여 물리 결함 수식 및 다운타임 연산 완전 해제 트리거
      const response = await fetch(`http://localhost:8000/api/v1/components/${targetComponent}/faults`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fault_code: Number(faultCode),
          intensity: 0.0,
        }),
      });

      if (response.ok) {
        setInjectionStatus(`✔ [정상 복구] 고장 상태가 전포 해제되었습니다. OEE 지표가 점진적으로 회복됩니다.`);
      } else {
        setInjectionStatus(`❌ 해제 실패`);
      }
    } catch (err: any) {
      setInjectionStatus(`❌ 예외: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-slate-950 border border-slate-800 p-6 rounded-xl shadow-xl flex flex-col space-y-4">
      <div>
        <h2 className="text-sm font-bold font-mono text-rose-500">ros2_medkit Fault Injection Operator</h2>
        <p className="text-xs font-mono text-slate-500">Programmatic Edge Disturbance Simulation Engine</p>
      </div>
      <hr className="border-slate-800" />

      <div className="space-y-3 font-mono text-xs">
        <div className="flex flex-col space-y-1">
          <label className="text-slate-400">TARGET COMPONENT BOUNDARY</label>
          <select
            value={targetComponent}
            onChange={(e) => setTargetComponent(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-rose-500"
          >
            <option value="amr_01_lidar">AMR_01 Lidar Sensor (Optical Component)</option>
            <option value="amr_01_wheel_joint">AMR_01 Actuator Saturation Joint</option>
            <option value="openplc_conveyor">OpenPLC Conveyor Belt Inverter</option>
          </select>
        </div>

        <div className="flex flex-col space-y-1">
          <label className="text-slate-400">FAULT MODE MATRIX</label>
          <select
            value={faultCode}
            onChange={(e) => setFaultCode(Number(e.target.value))}
            className="bg-slate-900 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-rose-500"
          >
            <option value={401}>Code 401: Sensing Drift & Blind (Lidar Optical Overray)</option>
            <option value={501}>Code 501: Stuck-Off / Actuator Break Circuit</option>
            <option value={601}>Code 601: Friction Degradation / Structural Wear</option>
          </select>
        </div>

        <div className="flex flex-col space-y-1">
          <div className="flex justify-between text-slate-400">
            <label>DISTURBANCE INTENSITY</label>
            <span className="text-rose-400 font-bold">{(intensity * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.1"
            max="1.0"
            step="0.1"
            value={intensity}
            onChange={(e) => setIntensity(Number(e.target.value))}
            className="w-full accent-rose-600 h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <button
          onClick={handleInjectFault}
          disabled={isLoading}
          className="bg-rose-700 hover:bg-rose-600 text-white font-mono font-bold text-xs py-3 rounded-lg transition shadow-md disabled:bg-slate-800 disabled:text-slate-500"
        >
          {isLoading ? 'PROCESSING...' : '🔥 INJECT FAULT'}
        </button>
        <button
          onClick={handleClearFault}
          disabled={isLoading}
          className="bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono font-bold text-xs py-3 rounded-lg transition border border-slate-700 disabled:bg-slate-800 disabled:text-slate-500"
        >
          {isLoading ? 'PROCESSING...' : '✔ CLEAR FAULT'}
        </button>
      </div>

      {injectionStatus && (
        <div className="bg-slate-900 border border-slate-800 p-3 rounded text-[11px] font-mono whitespace-pre-wrap leading-relaxed text-slate-300">
          {injectionStatus}
        </div>
      )}
    </div>
  );
};

export default FaultPanel;