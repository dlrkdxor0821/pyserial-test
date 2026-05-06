"""Round 4: 전체 경로 통합 시나리오 테스트"""
import math
from unittest.mock import MagicMock, call

TARGET_X = 3.0
TARGET_Y = 2.0
THRESHOLD = 0.5

results = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append(condition)
    suffix = f" ({detail})" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return condition

class MockPose:
    def __init__(self, x, y):
        self.pose = type('p', (), {'position': type('pos', (), {'x': x, 'y': y})()})()

class ServoLogicCore:
    def __init__(self, ser):
        self.ser = ser
        self.servo_active = False

    def pose_callback(self, msg):
        dx = msg.pose.position.x - TARGET_X
        dy = msg.pose.position.y - TARGET_Y
        dist = math.sqrt(dx**2 + dy**2)
        if self.ser is None:
            return
        if dist < THRESHOLD and not self.servo_active:
            self.ser.write(b'START\n')
            self.servo_active = True
        elif dist >= THRESHOLD and self.servo_active:
            self.ser.write(b'STOP\n')
            self.servo_active = False

print("=" * 60)
print("Round 4-A: 로봇 전체 경로 통합 시나리오")
print("출발→이동→목표도달→이탈→재도달")
print("=" * 60)

mock_ser = MagicMock()
node = ServoLogicCore(ser=mock_ser)

# 경로 정의: (x, y, 예상_servo_active, 예상_커맨드_or_None)
path = [
    (0.0,  0.0,  False, None),     # 출발
    (1.0,  0.0,  False, None),     # 이동 중
    (2.0,  1.0,  False, None),     # 이동 중
    (3.1,  2.1,  True,  b'START\n'), # 목표 도달
    (3.0,  2.0,  True,  None),     # 목표 내 머무름 (중복 START 없음)
    (2.9,  1.9,  True,  None),     # 목표 내 머무름 (dist≈0.141)
    (1.0,  0.5,  False, b'STOP\n'), # 이탈
    (2.5,  1.5,  False, None),     # 재접근 중 (dist≈0.707 > 0.5)
    (3.2,  2.2,  True,  b'START\n'), # 재도달
]

write_before = 0
for i, (x, y, expected_active, expected_cmd) in enumerate(path):
    write_count_before = mock_ser.write.call_count
    node.pose_callback(MockPose(x, y))
    write_count_after = mock_ser.write.call_count

    dist = math.sqrt((x - TARGET_X)**2 + (y - TARGET_Y)**2)
    label = f"({x},{y}) dist={dist:.3f}"

    # servo_active 상태 확인
    check(f"스텝 {i+1} {label} → servo_active={expected_active}",
          node.servo_active == expected_active)

    # 커맨드 발생 여부 확인
    if expected_cmd is None:
        check(f"스텝 {i+1} → 커맨드 없음",
              write_count_after == write_count_before)
    else:
        cmd_sent = write_count_after == write_count_before + 1
        if cmd_sent:
            actual_cmd = mock_ser.write.call_args_list[write_count_before]
            check(f"스텝 {i+1} → {expected_cmd} 발행",
                  actual_cmd == call(expected_cmd),
                  f"got {actual_cmd}")
        else:
            check(f"스텝 {i+1} → {expected_cmd} 발행", False, "커맨드 미발행")

print()
print("=" * 60)
print("Round 4-B: 전체 write() 시퀀스 검증")
print("=" * 60)

expected_sequence = [b'START\n', b'STOP\n', b'START\n']
actual_sequence = [c[0][0] for c in mock_ser.write.call_args_list]
check("전체 커맨드 시퀀스 = START→STOP→START",
      actual_sequence == expected_sequence,
      f"got {actual_sequence}")
check("총 write() 호출 = 3회",
      mock_ser.write.call_count == 3,
      f"got {mock_ser.write.call_count}")

print()
print("=" * 60)
print("Round 4-C: 최종 상태 확인")
print("=" * 60)
check("경로 종료 후 servo_active=True (마지막 위치가 목표 내)", node.servo_active == True)

# ──────────────────────────────────────────────
# 라운드별 결과 (이전 라운드 결과는 고정값 사용)
# ──────────────────────────────────────────────
r4_total = len(results)
r4_passed = sum(results)
r4_failed = r4_total - r4_passed

print()
print("=" * 60)
print("=== 최종 종합 테스트 결과 ===")
print("=" * 60)
print(f"라운드 1 (기본 START/STOP):          14/14 PASS")
print(f"라운드 2 (엣지케이스):               확인 필요")
print(f"라운드 3 (아두이노 + mock):          확인 필요")
print(f"라운드 4 (통합 경로 시나리오):       {r4_passed}/{r4_total} {'PASS' if r4_failed==0 else 'FAIL'}")
print("=" * 60)
if r4_failed == 0:
    print(f"라운드 4 전체 통과 ({r4_passed}/{r4_total})")
else:
    print(f"라운드 4 실패 {r4_failed}건")
