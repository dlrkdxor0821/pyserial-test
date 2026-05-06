"""Round 3: 아두이노 로직 시뮬레이션 + pyserial mock 통신 테스트"""
import math
import sys
from unittest.mock import MagicMock, patch, call

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
results = []

def check(name, condition):
    status = PASS if condition else FAIL
    print(f"  [{status}] {name}")
    results.append(condition)
    return condition

# ──────────────────────────────────────────────
# Part 1: 아두이노 ino 로직 Python 시뮬레이션
# ──────────────────────────────────────────────
print("\n=== Part 1: 아두이노 ino 로직 시뮬레이션 ===")

class ArduinoSimulator:
    """servo_sweep.ino 의 loop() 로직을 Python으로 재현"""
    def __init__(self):
        self.sweeping = False
        self.servo_pos = 90  # myServo.write(90) in setup()
        self.sweep_log = []

    def receive_command(self, raw_cmd: bytes):
        """readStringUntil('\n') + trim() 시뮬레이션"""
        cmd = raw_cmd.decode().rstrip('\n').strip()  # trim() = strip whitespace incl \r
        if cmd == "START":
            self.sweeping = True
        elif cmd == "STOP":
            self.sweeping = False
            self.servo_pos = 90

    def tick(self):
        """loop() 1사이클 (delay 제외)"""
        if self.sweeping:
            self.servo_pos = 0
            self.sweep_log.append(0)
            self.servo_pos = 180
            self.sweep_log.append(180)

print("\n[시나리오 A] START 커맨드 → sweeping 전환")
ard = ArduinoSimulator()
check("초기 sweeping=False", not ard.sweeping)
ard.receive_command(b'START\n')
check("START 후 sweeping=True", ard.sweeping)
ard.tick()
check("tick 후 sweep_log에 0, 180 기록", ard.sweep_log == [0, 180])

print("\n[시나리오 B] STOP 커맨드 → sweeping 해제 + 서보 90도 복귀")
ard2 = ArduinoSimulator()
ard2.receive_command(b'START\n')
ard2.tick()
ard2.receive_command(b'STOP\n')
check("STOP 후 sweeping=False", not ard2.sweeping)
check("STOP 후 servo_pos=90", ard2.servo_pos == 90)
ard2.tick()
check("STOP 후 tick에서 sweep_log 증가 없음", len(ard2.sweep_log) == 2)

print("\n[시나리오 C] \\r\\n 포함 커맨드 (Windows 줄바꿈 잠재적 버그)")
ard3 = ArduinoSimulator()
ard3.receive_command(b'START\r\n')
check("START\\r\\n → trim() 처리로 sweeping=True", ard3.sweeping)
ard3.receive_command(b'STOP\r\n')
check("STOP\\r\\n → trim() 처리로 sweeping=False", not ard3.sweeping)

print("\n[시나리오 D] 알 수 없는 커맨드 → 상태 유지")
ard4 = ArduinoSimulator()
ard4.receive_command(b'START\n')
ard4.receive_command(b'PAUSE\n')
check("PAUSE 커맨드 → sweeping 그대로 True", ard4.sweeping)
ard4.receive_command(b'RESET\n')
check("RESET 커맨드 → sweeping 그대로 True", ard4.sweeping)
ard4.receive_command(b'STOP\n')
ard4.receive_command(b'UNKNOWN\n')
check("STOP 후 UNKNOWN → sweeping 그대로 False", not ard4.sweeping)

# ──────────────────────────────────────────────
# Part 2: pyserial mock 통신 시뮬레이션
# ──────────────────────────────────────────────
print("\n=== Part 2: pyserial mock 통신 시뮬레이션 ===")

# servo_trigger_node의 핵심 로직만 추출 (rclpy 의존성 없이)
import math as _math

TARGET_X = 3.0
TARGET_Y = 2.0
THRESHOLD = 0.5

class MockPose:
    def __init__(self, x, y):
        self.pose = type('p', (), {'position': type('pos', (), {'x': x, 'y': y})()})()

class ServoLogicCore:
    """ServoTriggerNode의 순수 로직 (rclpy/serial 의존 제거)"""
    def __init__(self, ser):
        self.ser = ser
        self.servo_active = False

    def pose_callback(self, msg):
        dx = msg.pose.position.x - TARGET_X
        dy = msg.pose.position.y - TARGET_Y
        dist = _math.sqrt(dx**2 + dy**2)
        if self.ser is None:
            return
        if dist < THRESHOLD and not self.servo_active:
            self.ser.write(b'START\n')
            self.servo_active = True
        elif dist >= THRESHOLD and self.servo_active:
            self.ser.write(b'STOP\n')
            self.servo_active = False

    def destroy(self):
        if self.ser and getattr(self.ser, 'is_open', False):
            self.ser.write(b'STOP\n')
            self.ser.close()

print("\n[시나리오 E] 시리얼 포트 오픈 실패 시 크래시 없이 처리")
node_no_serial = ServoLogicCore(ser=None)
try:
    node_no_serial.pose_callback(MockPose(3.0, 2.0))
    check("ser=None일 때 pose_callback 크래시 없음", True)
    check("ser=None일 때 servo_active 변화 없음", not node_no_serial.servo_active)
except Exception as e:
    check(f"ser=None일 때 크래시 발생: {e}", False)
    check("ser=None일 때 servo_active 변화 없음", False)

print("\n[시나리오 F] ser.write() 호출 순서 검증")
mock_ser = MagicMock()
mock_ser.is_open = True
node = ServoLogicCore(ser=mock_ser)

node.pose_callback(MockPose(3.1, 2.1))   # dist ≈ 0.141 → START
node.pose_callback(MockPose(0.0, 0.0))   # dist ≈ 3.606 → STOP
node.pose_callback(MockPose(3.0, 2.0))   # dist = 0.0   → START
node.destroy()                            # → STOP + close

expected_calls = [
    call(b'START\n'),
    call(b'STOP\n'),
    call(b'START\n'),
    call(b'STOP\n'),
]
check("write() 호출 순서 일치", mock_ser.write.call_args_list == expected_calls)
check("destroy() 후 ser.close() 호출됨", mock_ser.close.called)

print("\n[시나리오 G] 연속 동일 위치 토픽 → 중복 write 없음")
mock_ser2 = MagicMock()
node2 = ServoLogicCore(ser=mock_ser2)

for _ in range(5):
    node2.pose_callback(MockPose(3.0, 2.0))  # 계속 목표 범위 내

check("5번 연속 진입 → write() 1번만 호출", mock_ser2.write.call_count == 1)
check("첫 호출은 START", mock_ser2.write.call_args_list[0] == call(b'START\n'))

for _ in range(3):
    node2.pose_callback(MockPose(0.0, 0.0))  # 계속 이탈 위치

check("3번 연속 이탈 → STOP 1번만 추가 호출", mock_ser2.write.call_count == 2)
check("두 번째 호출은 STOP", mock_ser2.write.call_args_list[1] == call(b'STOP\n'))

# ──────────────────────────────────────────────
# 최종 요약
# ──────────────────────────────────────────────
total = len(results)
passed = sum(results)
failed = total - passed

print(f"\n{'='*50}")
print(f"Round 3 결과: {passed}/{total} PASS", end="")
if failed == 0:
    print("  \033[32m전체 통과\033[0m")
else:
    print(f"  \033[31m{failed}건 실패\033[0m")
print('='*50)
sys.exit(0 if failed == 0 else 1)
