#include "rclcpp/rclcpp.hpp"
#include "behaviortree_cpp/loggers/bt_cout_logger.h"
#include "smart_factory_sim/nav_actions.hpp"
#include "std_msgs/msg/string.hpp"

// XML 트리 구조 정의 (메모리 다이렉트 주입형)
const std::string xml_text = R"(
 <root BTCPP_format="4">
     <BehaviorTree ID="AMR_Main_Mission_Tree">
         <Sequence name="vda5050_execution_sequence">
             <MoveToStation target_station="station_loading_01" current_status="{navigation_result}"/>
             <DockAndLift action_type="LIFT_CARGO"/>
         </Sequence>
     </BehaviorTree>
 </root>
)";

class BTMissionCoordinator : public rclcpp::Node {
public:
    BTMissionCoordinator() : Node("bt_mission_coordinator_node") {
        RCLCPP_INFO(this->get_logger(), "=========================================================================");
        RCLCPP_INFO(this->get_logger(), " 🧠 BehaviorTree.CPP v4 임무 조율 및 자율화 시퀀서 엔진 점화");
        RCLCPP_INFO(this->get_logger(), "=========================================================================");

        // 1. BT 노드 팩토리 등록
        factory_.registerNodeType<SmartFactory::MoveToStation>("MoveToStation");
        factory_.registerNodeType<SmartFactory::DockAndLift>("DockAndLift");

        // 2. XML 트리 빌딩 및 블랙보드 세션 인입
        tree_ = factory_.createTreeFromText(xml_text);
        
        // 3. 타이머 기반 BT 주기적 틱(Tick) 가동 (20Hz 주기 임무 관제)
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(50),
            std::bind(&BTMissionCoordinator::update_tree, this)
        );
    }

private:
    void update_tree() {
        BT::NodeStatus status = tree_.tickOnce();
        if (status == BT::NodeStatus::SUCCESS) {
            RCLCPP_INFO(this->get_logger(), "🎉 [임무 마감] 전체 VDA 5050 라우팅 시퀀스가 성공적으로 마감되었습니다. 트리 가동 일시 유도.");
            timer_->cancel(); // 1회 공정 완료 시 타이머 락킹
        } else if (status == BT::NodeStatus::FAILURE) {
            RCLCPP_ERROR(this->get_logger(), "❌ [임무 실패] 행동 트리 내 결함 포착. 비상 정지(Safety Fail-Safe) 발동.");
            timer_->cancel();
        }
    }

    BT::BehaviorTreeFactory factory_;
    BT::Tree tree_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<BTMissionCoordinator>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}