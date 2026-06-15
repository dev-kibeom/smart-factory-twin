# factory_interfaces/msg/SafetyStatus.msg
# [URS-02/FRS-02.2] 가상 Soft-PLC 및 로봇 간의 실시간 필드버스 동기화 및 인터록용 산업용 메시지 명세 

bool is_safety_interlock_ok      # OpenPLC 안전 인터록 정상 여부 (True: 정상, False: 차단) 
bool emergency_stop_triggered    # 비상정지(E-Stop) 작동 여부 (True: 비상정지, False: 해제) 