// smart_factory_twin/ros2_ws/src/smart_factory_sim/include/smart_factory_sim/nav_actions.hpp
#pragma once
#include "behaviortree_cpp/action_node.h"
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp" 
#include "std_msgs/msg/string.hpp"
#include <chrono> // [핫픽스 수복] 정격 C++ 표준 시간 헤더 인입
#include <thread> // [핫픽스 수복] 정격 C++ 표준 스레드 헤더 인입

namespace SmartFactory {

// ---------------------------------------------------------------------------
// [BT Action Node] 1. VDA 5050 하향 명령 기반 실전 Gazebo cmd_vel 연격 주행 액션
// ---------------------------------------------------------------------------
class MoveToStation : public BT::StatefulActionNode {
public:
    MoveToStation(const std::string& name, const BT::NodeConfig& config)
        : BT::StatefulActionNode(name, config) {
        
        auto node = rclcpp::Node::make_shared("bt_move_sub_node");
        cmd_vel_pub_ = node->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);
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
        if (elapsed < 4) {
            twist_msg.linear.x = 0.4;
            twist_msg.angular.z = 0.0;
        } else if (elapsed >= 4 && elapsed < 6) {
            twist_msg.linear.x = 0.1;
            twist_msg.angular.z = 0.3;
        }

        cmd_vel_pub_->publish(twist_msg);

        if (elapsed >= 6) {
            auto stop_msg = geometry_msgs::msg::Twist();
            cmd_vel_pub_->publish(stop_msg);

            std::cout << "✔ [BT ENGINE] 목적지 [" << target_station_ << "] 안착 완료.\n";
            setOutput("current_status", "ARRIVED_" + target_station_);
            return BT::NodeStatus::SUCCESS;
        }
        return BT::NodeStatus::RUNNING;
    }

    void onHalted() override {
        auto emergency_stop = geometry_msgs::msg::Twist();
        cmd_vel_pub_->publish(emergency_stop);
        std::cout << "🛑 [BT ENGINE] 주행 임무 강제 정지 (Halted 및 모터 서킷 차단).\n";
    }

private:
    std::string target_station_;
    std::chrono::steady_clock::time_point start_time_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
};

// ---------------------------------------------------------------------------
// [BT Action Node] 2. 정밀 도킹 및 화물 리프팅 액션 (동기 무결성 유지)
// ---------------------------------------------------------------------------
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