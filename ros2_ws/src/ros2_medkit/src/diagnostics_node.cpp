#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <factory_interfaces/srv/inject_fault.hpp> // 앞서 빌드 성공한 커스텀 인터페이스 수입

class DiagnosticsNode : public rclcpp::Node {
public:
    DiagnosticsNode() : Node("diagnostics_node") {
        // 1. 프로그래머틱 고장 주입 REST API와 연격될 ROS2 동기식 서비스 서버 개방
        fault_srv_ = this->create_service<factory_interfaces::srv::InjectFault>(
            "/ros2_medkit/inject_fault",
            std::bind(&DiagnosticsNode::handle_fault_injection, this, std::placeholders::_1, std::placeholders::_2)
        );

        // 2. 물리 센서 데이터를 가로채서 수식적 결함 실패 모델을 인가할 변조 프록시 파이프라인
        scan_sub_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
            "/scan_raw", 10, std::bind(&DiagnosticsNode::scan_callback, this, std::placeholders::_1)
        );
        scan_pub_ = this->create_publisher<sensor_msgs::msg::LaserScan>("/scan", 10);
        
        active_fault_code_ = 0; // 0: 정상 상태 (Operational)
        RCLEXP_INFO(this->get_logger(), "SOVD 규격 모사 ros2_medkit 진단 코어 엔진 점화 완료.");
    }

private:
    void handle_fault_injection(
        const std::shared_ptr<factory_interfaces::srv::InjectFault::Request> request,
        std::shared_ptr<factory_interfaces::srv::InjectFault::Response> response) 
    {
        active_fault_code_ = request->fault_code;
        noise_scale_ = request->noise_bias;
        response->is_success = true;
        RCLCPP_WARN(this->get_logger(), "🚨 [결함 인가] Component: %s | Code: %d 주입 완정.", 
            request->component_id.c_str(), request->fault_code);
    }

    void scan_callback(const sensor_msgs::msg::LaserScan::SharedPtr msg) {
        auto modified_scan = *msg;
        
        // [Sensing Drift & Bias 수학적 실패 모델 주입 레이어]
        if (active_fault_code_ == 401) { // Lidar Blind 에러 상황 모사 
            for (auto& range : modified_scan.ranges) {
                range = std::numeric_limits<float>::infinity(); // 거리 배열을 inf로 동적 전포 변경
            }
        }
        scan_pub_->publish(modified_scan);
    }

    rclcpp::Service<factory_interfaces::srv::InjectFault::Client>::SharedPtr fault_srv_;
    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;
    rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr scan_pub_;
    int32_t active_fault_code_;
    double noise_scale_;
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<DiagnosticsNode>());
    rclcpp::shutdown();
    return 0;
}