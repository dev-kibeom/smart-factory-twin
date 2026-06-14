#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = rclcpp::Node::make_shared("bt_engine_node");
    RCLCPP_INFO(node->get_logger(), "BehaviorTree.CPP v4 임무 제어 엔진 및 진단 링크 스텁 점화 완료.");
    rclcpp::shutdown();
    return 0;
}
