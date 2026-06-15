#pragma once
#include "behaviortree_cpp/action_node.h"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include <iostream>

namespace SmartFactory {

// ---------------------------------------------------------------------------
// [BT Action Node] 1. VDA 5050 하향 명령 기반 타겟 노드 주행 액션
// ---------------------------------------------------------------------------
class MoveToStation : public BT::StatefulActionNode {
public:
    MoveToStation(const std::string& name, const BT::NodeConfig& config)
        : BT::StatefulActionNode(name, config) {}

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
        // JAX 가속 물리 평면 주행 타임 오버레이 모사 (실제 공정 주행 마진 2초 확보)
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time_).count();

        if (elapsed >= 2) {
            std::cout << "✔ [BT ENGINE] 목적지 [" << target_station_ << "] 안착 완료.\n";
            setOutput("current_status", "ARRIVED_" + target_station_);
            return BT::NodeStatus::SUCCESS;
        }
        return BT::NodeStatus::RUNNING;
    }

    void onHalted() override {
        std::cout << "🛑 [BT ENGINE] 주행 임무 강제 정지 (Halted).\n";
    }

private:
    std::string target_station_;
    std::chrono::steady_clock::time_point start_time_;
};

// ---------------------------------------------------------------------------
// [BT Action Node] 2. 정밀 도킹 및 화물 리프팅 액션
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
        std::this_thread::sleep_for(std::chrono::milliseconds(800)); // 동기 가드가 깨지지 않는 선에서 슬립 제어
        std::cout << "✔ [BT ENGINE] 화물 체결 무결성 확보 성공.\n";
        return BT::NodeStatus::SUCCESS;
    }
};

} // namespace SmartFactory