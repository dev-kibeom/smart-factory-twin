// smart_factory_twin/ros2_ws/src/smart_factory_sim/src/ros2_opc_ua_bridge_node.cpp
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "std_msgs/msg/bool.hpp"
#include "open62541/client_config_default.h"
#include "open62541/client_highlevel.h"
#include <chrono>
#include <memory>

using namespace std::chrono_literals;

class Ros2OpcUaBridgeNode : public rclcpp::Node {
public:
    Ros2OpcUaBridgeNode() : Node("ros2_opc_ua_bridge_node"), opc_client_(nullptr), is_connected_(false) {
        
        // 1. ROS2 전포 서킷 퍼블리셔 및 서브스크라이버 바인딩
        // 행동 트리 및 VDA 5050 커넥터 평면과 통전할 내부 상태 채널 개통
        amr_status_sub_ = this->create_subscription<std_msgs::msg::String>(
            "/amr_fleet/status", 10,
            std::bind(&Ros2OpcUaBridgeNode::amr_status_callback, this, std::placeholders::_1));

        plc_signal_pub_ = this->create_publisher<std_msgs::msg::Bool>("/factory/plc_handshake_done", 10);

        // 2. open62541 정격 클라이언트 인스턴스 초기화 및 세션을 메모리에 적재
        opc_client_ = UA_Client_new();
        UA_ClientConfig_setDefault(UA_Client_getConfig(opc_client_));

        // 3. 인프라 데몬 감시용 10Hz 주기적 OPC UA 상태 폴링 및 하트비트 타이머 구동
        heartbeat_timer_ = this->create_wall_timer(
            100ms, std::bind(&Ros2OpcUaBridgeNode::maintain_opc_connection_and_heartbeat, this));

        RCLCPP_INFO(this->get_logger(), "🔌 [OPC UA BRIDGE] 로봇-PLC 공정 핸드셰이크 관문 노드가 정상 점화되었습니다.");
    }

    ~Ros2OpcUaBridgeNode() {
        if (opc_client_) {
            UA_Client_disconnect(opc_client_);
            UA_Client_delete(opc_client_);
        }
    }

private:
    // ===========================================================================
    // 🛡️ [하트비트 가드] OpenPLC 와의 통신 무결성 및 리커버리 세션 자동 추종
    // ===========================================================================
    void maintain_opc_connection_and_heartbeat() {
        if (!is_connected_) {
            // docker-compose 망 내부의 OpenPLC 정격 포트(4840)로 세션 연결 직격 시도
            UA_StatusCode retval = UA_Client_connect(opc_client_, "opc.tcp://openplc:4840");
            if (retval == UA_STATUSCODE_GOOD) {
                RCLCPP_INFO(this->get_logger(), "✔ [OPC UA CONNECT] OpenPLC Soft-PLC 레지스터 서버망과 정상 통전 수립 완료.");
                is_connected_ = true;
            } else {
                RCLCPP_WARN(this->get_logger(), "⏳ [OPC UA RETRY] OpenPLC 관문이 닫혀있습니다. 100ms 후 재통전을 시도합니다...");
                is_connected_ = false;
                return;
            }
        }

        // 20Hz 상호 하트비트 생존 카운터를 PLC 레지스터에 상향 기록하여 통신 결함 유실 차단
        static int heartbeat_cnt = 0;
        UA_Variant value;
        UA_Variant_init(&value);
        UA_Variant_setScalar(&value, &heartbeat_cnt, &UA_TYPES[UA_TYPES_INT32]);
        
        // ns=2;s=AMR_Heartbeat 주소 장부에 데이터 인서트
        UA_Client_writeValueAttribute(opc_client_, 
            UA_NODEID_STRING(2, const_cast<char*>("AMR_Heartbeat")), &value);
        
        heartbeat_cnt = (heartbeat_cnt + 1) % 10000;

        // 실시간으로 PLC의 Loading_Done 코일 장부를 감시(Polling)
        check_plc_loading_interlock();
    }

    // ===========================================================================
    // 📥 [ROS2 인입 스냅샷] 행동 트리 주행 결과에 따른 PLC 레지스터 강제 인서트
    // ===========================================================================
    void amr_status_callback(const std_msgs::msg::String::SharedPtr msg) {
        if (!is_connected_ || !opc_client_) return;

        // 아까 행동 트리가 최종 완정 사출한 "ARRIVED_station_loading_01" 문자열 패턴 매칭 가드
        if (msg->data == "ARRIVED_station_loading_01") {
            RCLCPP_INFO(this->get_logger(), "🤖 [AMR EVENT] 로봇이 로딩 존에 하드웨어 안착했습니다. PLC 인터록 코일을 올립니다.");
            
            UA_Boolean arrived_flag = true;
            UA_Variant value;
            UA_Variant_init(&value);
            UA_Variant_setScalar(&value, &arrived_flag, &UA_TYPES[UA_TYPES_BOOLEAN]);

            // OpenPLC 노드 인덱스 ns=2;s=AMR_Arrived 에 로봇 안착 신호 강제 락인
            UA_Client_writeValueAttribute(opc_client_, 
                UA_NODEID_STRING(2, const_cast<char*>("AMR_Arrived")), &value);
        }
    }

    // ===========================================================================
    // ⚙️ [공정 인터록] Soft-PLC 물리 컨베이어 구동 완료 이벤트 가치 동기화
    // ===========================================================================
    void check_plc_loading_interlock() {
        if (!is_connected_ || !opc_client_) return;

        UA_Variant val;
        UA_Variant_init(&val);
        
        // OpenPLC 내부 물리 컨베이어 반전 공정이 끝나서 PLC_Loading_Done 코일이 트루인지 실시간 획득
        UA_StatusCode retval = UA_Client_readValueAttribute(opc_client_, 
            UA_NODEID_STRING(2, const_cast<char*>("PLC_Loading_Done")), &val);

        if (retval == UA_STATUSCODE_GOOD && UA_Variant_isScalar(&val) && val.type == &UA_TYPES[UA_TYPES_BOOLEAN]) {
            UA_Boolean is_done = *(UA_Boolean*)val.data;
            
            if (is_done) {
                RCLCPP_INFO(this->get_logger(), "🏭 [PLC HANDSHAKE] Soft-PLC 물리 반전 기계 공정 종료 신호 수전! ROS2 버스망에 전포 사출.");
                
                // 1. 상위 행동 트리 제어권을 다음 시퀀스로 넘기기 위한 동기화 토픽 발행
                std_msgs::msg::Bool done_msg;
                done_msg.data = true;
                plc_signal_pub_->publish(done_msg);

                // 2. 트랜잭션 종료 확인을 완료했으므로 상호 인터록 해제를 위해 Arrived 코일 원복 클리어
                UA_Boolean reset_flag = false;
                UA_Variant reset_val;
                UA_Variant_init(&reset_val);
                UA_Variant_setScalar(&reset_val, &reset_flag, &UA_TYPES[UA_TYPES_BOOLEAN]);
                UA_Client_writeValueAttribute(opc_client_, 
                    UA_NODEID_STRING(2, const_cast<char*>("AMR_Arrived")), &reset_val);
            }
        }
        UA_Variant_clear(&val);
    }

    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr amr_status_sub_;
    rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr plc_signal_pub_;
    rclcpp::TimerBase::SharedPtr heartbeat_timer_;
    UA_Client* opc_client_;
    bool is_connected_;
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<Ros2OpcUaBridgeNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}