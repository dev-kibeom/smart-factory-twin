# [factory_interfaces] 가상 AMR 런타임 동역학 최적화 결과 보고 메시지
std_msgs/Header header

string robot_id           # 로봇 고유 식별 명칭 (예: amr_01)
float64 estimated_inertia # JAX 최적화 수렴 관성 모멘트 [cite: 424]
float64 estimated_friction# JAX 최적화 수렴 관절 마찰 계수 [cite: 424]
float64 joint_torque_nm   # 현재 4축 디퍼런셜 조인트 총합 토크 실측치 (Nm)
string system_status      # 에이전트 가동 상태 제어 플래그 (OPERATIONAL / FAULT)