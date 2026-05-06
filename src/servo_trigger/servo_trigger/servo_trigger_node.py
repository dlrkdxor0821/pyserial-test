import math
import threading
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import serial

THRESHOLD = 0.5
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

# 트리거 좌표 (x, y, z) — z는 0으로 고정
TRIGGER_COORDS = [
    (1.0, 1.0, 0.0),
    (2.0, 2.0, 0.0),
    (3.0, 3.0, 0.0),
    (4.0, 4.0, 0.0),
    (5.0, 5.0, 0.0),
]


class ServoTriggerNode(Node):
    def __init__(self):
        super().__init__('servo_trigger_node')
        self.triggered_coords = set()  # 이미 실행된 좌표 (세션 내 재실행 방지)
        self.animation_running = False

        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            self.get_logger().info(f'Serial port {SERIAL_PORT} opened')
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open serial port: {e}')
            self.ser = None

        self.subscription = self.create_subscription(
            PoseStamped,
            '/pose',
            self.pose_callback,
            10
        )

    def pose_callback(self, msg):
        if self.animation_running:
            return

        x = msg.pose.position.x
        y = msg.pose.position.y
        z = msg.pose.position.z

        self.get_logger().debug(f'Current pose: x={x:.2f} y={y:.2f} z={z:.2f}')

        if self.ser is None:
            self.get_logger().warn('Serial not connected, skipping trigger check.')
            return

        for coord in TRIGGER_COORDS:
            if coord in self.triggered_coords:
                continue
            dx = x - coord[0]
            dy = y - coord[1]
            dz = z - coord[2]
            dist = math.sqrt(dx**2 + dy**2 + dz**2)
            if dist < THRESHOLD:
                self.triggered_coords.add(coord)
                self.get_logger().info(
                    f'Triggered! x:{coord[0]} y:{coord[1]} z:{coord[2]} (dist={dist:.3f})'
                )
                self._start_nod_sequence()
                break

    def _start_nod_sequence(self):
        # t=0s  : LEFT   (정면→왼쪽, 90°, 1초)
        # t=1s  : RIGHT  (왼쪽→오른쪽, 180°, 2초)
        # t=3s  : CENTER (오른쪽→정면, 90°, 1초)
        # t=4s  : 완료
        self.animation_running = True
        self._send('LEFT')
        threading.Timer(1.0, self._send, args=('RIGHT',)).start()
        threading.Timer(3.0, self._send, args=('CENTER',)).start()
        threading.Timer(4.0, self._finish_animation).start()

    def _finish_animation(self):
        self.animation_running = False
        self.get_logger().info('Nod sequence complete.')

    def _send(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write(f'{cmd}\n'.encode())
            self.get_logger().info(f'Sent: {cmd}')

    def destroy_node(self):
        if self.ser and self.ser.is_open:
            self._send('CENTER')
            self.ser.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ServoTriggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
