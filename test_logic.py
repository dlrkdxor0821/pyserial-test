import math

TARGET_X = 3.0
TARGET_Y = 2.0
THRESHOLD = 0.5


class MockSerial:
    def __init__(self):
        self.sent = []
        self.is_open = True

    def write(self, data):
        self.sent.append(data)


class ServoLogic:
    def __init__(self, ser):
        self.servo_active = False
        self.ser = ser

    def pose_callback(self, x, y):
        dx = x - TARGET_X
        dy = y - TARGET_Y
        dist = math.sqrt(dx**2 + dy**2)

        if self.ser is None:
            return None

        if dist < THRESHOLD and not self.servo_active:
            self.ser.write(b'START\n')
            self.servo_active = True
            return 'START'
        elif dist >= THRESHOLD and self.servo_active:
            self.ser.write(b'STOP\n')
            self.servo_active = False
            return 'STOP'
        return None


def run_tests():
    passed = 0
    failed = 0

    def check(name, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name} — expected={expected}, got={actual}")
            failed += 1

    # ── Round 1: 기본 START/STOP 흐름 ──────────────────────────────────────
    print("\n[Round 1] 기본 START → STOP 흐름")
    ser = MockSerial()
    logic = ServoLogic(ser)

    result = logic.pose_callback(3.1, 2.1)      # dist ≈ 0.141 < 0.5
    check("(3.1,2.1) → START 발행", result, 'START')
    check("servo_active=True", logic.servo_active, True)

    result = logic.pose_callback(0.0, 0.0)      # dist ≈ 3.606 >= 0.5
    check("(0.0,0.0) → STOP 발행", result, 'STOP')
    check("servo_active=False", logic.servo_active, False)

    # ── Round 2: 정확한 목표 좌표 도달 ────────────────────────────────────
    print("\n[Round 2] 정확한 목표 좌표 (3.0, 2.0)")
    ser2 = MockSerial()
    logic2 = ServoLogic(ser2)

    result = logic2.pose_callback(3.0, 2.0)     # dist = 0.0
    check("(3.0,2.0) → START 발행", result, 'START')
    check("servo_active=True", logic2.servo_active, True)

    result = logic2.pose_callback(3.0, 2.0)     # 이미 active, 중복 방지
    check("중복 도달 시 None (중복 전송 없음)", result, None)

    # ── Round 3: 경계값 테스트 ─────────────────────────────────────────────
    print("\n[Round 3] THRESHOLD 경계값 (dist ≈ 0.566 > 0.5)")
    ser3 = MockSerial()
    logic3 = ServoLogic(ser3)

    dist_boundary = math.sqrt((3.4 - 3.0)**2 + (2.4 - 2.0)**2)
    result = logic3.pose_callback(3.4, 2.4)     # dist ≈ 0.566 >= 0.5
    check(f"(3.4,2.4) dist={dist_boundary:.3f} → None (THRESHOLD 밖)", result, None)
    check("servo_active=False 유지", logic3.servo_active, False)

    # ── Round 4: 이탈 후 재진입 사이클 ────────────────────────────────────
    print("\n[Round 4] 이탈 후 재진입 사이클")
    ser4 = MockSerial()
    logic4 = ServoLogic(ser4)

    logic4.pose_callback(3.1, 2.1)              # START
    check("진입 후 START", logic4.servo_active, True)

    logic4.pose_callback(0.0, 0.0)              # STOP
    check("이탈 후 STOP", logic4.servo_active, False)

    result = logic4.pose_callback(3.2, 1.9)     # 재진입 dist ≈ 0.224
    check("재진입 → START 재발행", result, 'START')
    check("servo_active=True 복귀", logic4.servo_active, True)

    serial_log = [d.decode() for d in ser4.sent]
    check("시리얼 전송 순서: START→STOP→START", serial_log, ['START\n', 'STOP\n', 'START\n'])

    # ── 결과 요약 ──────────────────────────────────────────────────────────
    print(f"\n{'='*45}")
    print(f"결과: {passed} PASS / {failed} FAIL")
    if failed == 0:
        print("모든 테스트 PASS ✓")
    else:
        print("일부 테스트 FAIL — 로직 수정 필요")
    return failed


if __name__ == '__main__':
    exit(run_tests())
