// smart_factory_twin/ros2_ws/src/smart_factory_sim/src/bt_mission_coordinator.cpp
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "sensor_msgs/msg/laser_scan.hpp" // 실제 가상 라이다 메시지 타입 인입
#include "behaviortree_cpp/behavior_tree.h"
#include "behaviortree_cpp/bt_factory.h"
#include "smart_factory_sim/nav_actions.hpp"
#include <chrono>
#include <memory>
#include <thread>

using namespace std::chrono_literals;

// 라이다 물리 센서 데이터 실시간 상태 가드 플래그
static bool g_is_lidar_blind = false;

// ---------------------------------------------------------------------------
// [BT Condition Node] 1. 라이다 물리 센서 오염도 실시간 판정 가드
// ---------------------------------------------------------------------------
class IsLidarHealthy : public BT::ConditionNode {
public:
    IsLidarHealthy(const std::string& name, const BT::NodeConfig& config)
        : BT::ConditionNode(name, config) {}
    static BT::PortsList providedPorts() { return {}; }

    BT::NodeStatus tick() override {
        // 실제 diagnostics_node에 의해 센서 물리 레이어가 inf로 오염되었는지 판정
        if (g_is_lidar_blind) {
            std::cout << "⚠️ [BT GUARD] 물리 센서 레벨 결함 수전! 라이다 차단 장치(Blind)가 작동합니다.\n";
            return BT::NodeStatus::FAILURE;
        }
        return BT::NodeStatus::SUCCESS;
    }
};

class ReportFaultToMqtt : public BT::SyncActionNode {
public:
    ReportFaultToMqtt(const std::string& name, const BT::NodeConfig& config)
        : BT::SyncActionNode(name, config) {
        auto node = rclcpp::Node::make_shared("bt_mqtt_reporter_sub_node");
        mqtt_trigger_pub_ = node->create_publisher<std_msgs::msg::String>("/amr_fleet/fault_report", 10);
    }
    static BT::PortsList providedPorts() { return {}; }

    BT::NodeStatus tick() override {
        std::cout << "🚨 [BT ACTION] 자율 Fail-Safe 구동: MQTT 관문 경유 VDA 5050 예외 알람 상향 사출.\n";
        auto msg = std_msgs::msg::String();
        msg.data = "{\"errorType\": 401, \"errorLevel\": \"FATAL\", \"description\": \"AMR_01 Lidar Sensor Blind\"}";
        mqtt_trigger_pub_->publish(msg);
        return BT::NodeStatus::SUCCESS;
    }
private:
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr mqtt_trigger_pub_;
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = rclcpp::Node::make_shared("bt_mission_coordinator_node");

    RCLCPP_INFO(node->get_logger(), "=========================================================================");
    RCLCPP_INFO(node->get_logger(), "  🧠 BehaviorTree.CPP v4 자율 결함 예외 차단 및 미션 제어 엔진 점화");
    RCLCPP_INFO(node->get_logger(), "=========================================================================");

    // 🔌 [실전 센서 검사 채널] diagnostics_node 가 가공하여 뿜어내는 /scan 토픽 실시간 감시 폴링
    auto scan_sub = node->create_subscription<sensor_msgs::msg::LaserScan>(
        "/scan", 10,
        [](const sensor_msgs::msg::LaserScan::SharedPtr msg) {
            if (!msg->ranges.empty() && msg->ranges[0] == std::numeric_limits<float>::infinity()) {
                g_is_lidar_blind = true; // 센서 데이터 전체가 inf로 박살났음을 실시간 락인 감지
            } else {
                g_is_lidar_blind = false;
            }
        });

    std::thread ros_spin_thread([node]() {
        rclcpp::spin(node);
    });
    ros_spin_thread.detach(); 

    BT::BehaviorTreeFactory factory;
    factory.registerBuilder<SmartFactory::MoveToStation>("MoveToStation",
        [node](const std::string& name, const BT::NodeConfig& config) {
            return std::make_unique<SmartFactory::MoveToStation>(name, config, node);
        });
        
    factory.registerBuilder<SmartFactory::DockAndLift>("DockAndLift");
    factory.registerFileType<IsLidarHealthy>("IsLidarHealthy");
    factory.registerFileType<ReportFaultToMqtt>("ReportFaultToMqtt");

    const std::string xml_text = R"(
    <root BTCPP_format="4">
        <BehaviorTree ID="MainTree">
            <Fallback name="Root_Exception_Bridge">
                <ReactiveSequence name="Safe_Mission_Route">
                    <IsLidarHealthy/>
                    <Sequence name="Mission_Steps">
                        <MoveToStation target_station="station_loading_01" current_status="{status}"/>
                        <DockAndLift action_type="LIFT_CARGO"/>
                    </Sequence>
                </ReactiveSequence>
                <ReportFaultToMqtt/>
            </Fallback>
        </BehaviorTree>
    </root>
    )";

    auto tree = factory.createTreeFromText(xml_text);

    rclcpp::Rate rate(20);
    while (rclcpp::ok()) {
        tree.tickOnce();
        rate.sleep();
    }

    rclcpp::shutdown();
    return 0;
}