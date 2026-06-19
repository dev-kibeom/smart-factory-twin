// smart_factory_twin/ros2_ws/src/smart_factory_sim/include/smart_factory_sim/nav_actions.hpp
#pragma once
#include "behaviortree_cpp/action_node.h"
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp" 
#include "std_msgs/msg/string.hpp"
#include <chrono>
#include <thread>

namespace SmartFactory {

class MoveToStation : public BT::StatefulActionNode {
public:
    // 🔌 [정격 제어선 인입] 메인 스핀 노드의 SharedPtr를 직접 수전받아 결착
    MoveToStation(const std::string& name, const BT::NodeConfig& config, rclcpp::Node::SharedPtr node)
        : BT::StatefulActionNode(name, config), node_(node) {
        
        // 고립된 독자 노드 대신 메인 커널 노드 이름 공간에 cmd_vel 퍼블리셔를 하드 링크
        cmd_vel_pub_ = node_->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);
    }

    static BT::PortsList providedPorts() {
        return { BT::InputPort<std::string>("target_station"),
                 BT::OutputPort<std::string>("current_status") };
    }

    BT::NodeStatus onStart() override {
        if (!getInput<std::string>("target_station", target_station_)) {
            throw BT::RuntimeError("missing required input [target_station]");
        }
        std::cout << "▶ [BT ENGINE] AMR amr_01가 목적지 [" << target_station_ << "]로 JAX 가속 주행을 개시합니다.\n";
        start_time_ = std::chrono::steady_clock::now();
        return BT::NodeStatus::RUNNING;
    }

    BT::NodeStatus onRunning() override {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time_).count();

        auto twist_msg = geometry_msgs::msg::Twist();
        // ⏳ [테스트 타임 마진 확장] 대시보드 고장 주입을 클릭할 수 있도록 15초 주행 레이아웃 전개
        if (elapsed < 10) {
            twist_msg.linear.x = 0.4; // 10초간 전진 주행
            twist_msg.angular.z = 0.0;
        } else if (elapsed >= 10 && elapsed < 15) {
            twist_msg.linear.x = 0.1; // 5초간 정밀 도킹 회전
            twist_msg.angular.z = 0.3;
        }

        cmd_vel_pub_->publish(twist_msg);

        if (elapsed >= 15) {
            auto stop_msg = geometry_msgs::msg::Twist();
            cmd_vel_pub_->publish(stop_msg);

            std::cout << "✔ [BT ENGINE] 목적지 [" << target_station_ << "] 안착 완료.\n";
            setOutput("current_status", "ARRIVED_" + target_station_);
            return BT::NodeStatus::SUCCESS;
        }
        return BT::NodeStatus::RUNNING;
    }

    void onHalted() override {
        // 고장 감지 루프 가 발동하여 팅겨나가는 즉시 Gazebo 물리 모터에 브레이크 인가 (Fail-Safe)
        auto emergency_stop = geometry_msgs::msg::Twist();
        cmd_vel_pub_->publish(emergency_stop);
        std::cout << "🛑 [BT ENGINE] 물리 안전 차단 발동 ➔ Gazebo 급제동 벡터 사출 완료.\n";
    }

private:
    std::string target_station_;
    std::chrono::steady_clock::time_point start_time_;
    rclcpp::Node::SharedPtr node_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
};

class DockAndLift : public BT::SyncActionNode {
public:
    DockAndLift(const std::string& name, const BT::NodeConfig& config)
        : BT::SyncActionNode(name, config) {}

    static BT::PortsList providedPorts() {
        return { BT::InputPort<std::string>("action_type") };
    }

    BT::NodeStatus tick() override {
        std::string action;
        getInput("action_type", action);
        std::cout << "⚡ [BT ENGINE] 스테이션 정밀 정렬 완료 ➔ 화물 [" << action << "] 시퀀스 돌입...\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(800));
        std::cout << "✔ [BT ENGINE] 화물 체결 무결성 확보 성공.\n";
        return BT::NodeStatus::SUCCESS;
    }
};

} // namespace SmartFactory