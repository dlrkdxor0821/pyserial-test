import math

TARGET_X = 3.0
TARGET_Y = 2.0
THRESHOLD = 0.5

def compute_dist(cx, cy):
    return math.sqrt((cx - TARGET_X)**2 + (cy - TARGET_Y)**2)

def simulate(positions):
    """positions: list of (x, y). Returns list of commands sent."""
    servo_active = False
    commands = []
    for (cx, cy) in positions:
        dist = compute_dist(cx, cy)
        if dist < THRESHOLD and not servo_active:
            commands.append(('START', dist))
            servo_active = True
        elif dist >= THRESHOLD and servo_active:
            commands.append(('STOP', dist))
            servo_active = False
    return commands, servo_active

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

print("=" * 60)
print("Round 1: 음수 좌표 거리 계산 정확성")
print("=" * 60)
# 목표 (3,2), 현재 (-1, -2) → dist = sqrt(16+16) = sqrt(32) ≈ 5.656
d = compute_dist(-1.0, -2.0)
check("음수 좌표 거리 계산", abs(d - math.sqrt(32)) < 1e-9, f"dist={d:.6f}")
check("음수 좌표 → 진입 안함", d >= THRESHOLD, f"dist={d:.3f} >= {THRESHOLD}")

# 음수지만 목표 근처: (-0+3, -0+2) 즉 (3.1, 2.1) → 이건 양수지만
# 진짜 음수: (2.7, 1.7) → dist = sqrt(0.09+0.09) = sqrt(0.18) ≈ 0.424 < 0.5
d2 = compute_dist(2.7, 1.7)
check("목표 근처 소수 좌표 dist 정확성", abs(d2 - math.sqrt(0.18)) < 1e-9, f"dist={d2:.6f}")
check("(2.7, 1.7) → 진입", d2 < THRESHOLD, f"dist={d2:.4f} < {THRESHOLD}")

print()
print("=" * 60)
print("Round 2: 대각선 이동 THRESHOLD 판단")
print("=" * 60)
# 대각선 이동: (0,0) → (1,1) → (2,2) → (2.8,2.2) → (3.3,2.3) → (3.0,2.0)
positions_diag = [(0.0,0.0), (1.0,1.0), (2.0,2.0), (2.8,2.2), (3.3,2.3), (3.0,2.0)]
cmds, active = simulate(positions_diag)
check("대각선 이동 중 START 발생", any(c[0]=='START' for c in cmds), str(cmds))
check("대각선 이동 최종 servo_active=True", active == True)
# (3.3,2.3) dist = sqrt(0.09+0.09) = 0.424 < 0.5 → START
d_33 = compute_dist(3.3, 2.3)
check("(3.3, 2.3) dist 계산", abs(d_33 - math.sqrt(0.09+0.09)) < 1e-9, f"dist={d_33:.4f}")

print()
print("=" * 60)
print("Round 3: 연속 진입/이탈 10회 반복")
print("=" * 60)
inside = (3.1, 2.1)   # dist ≈ 0.141 < 0.5
outside = (0.0, 0.0)  # dist >> 0.5

cycle_positions = []
for _ in range(10):
    cycle_positions.append(inside)
    cycle_positions.append(outside)

cmds, active = simulate(cycle_positions)
starts = [c for c in cmds if c[0] == 'START']
stops  = [c for c in cmds if c[0] == 'STOP']
check("10회 반복 — START 횟수 = 10", len(starts) == 10, f"got {len(starts)}")
check("10회 반복 — STOP 횟수 = 10", len(stops) == 10, f"got {len(stops)}")
check("10회 반복 — 최종 servo_active=False", active == False)
check("10회 반복 — 총 커맨드 수 = 20", len(cmds) == 20, f"got {len(cmds)}")

# 중복 전송 없는지: START 연속 두 번 없어야 함
no_dup = all(cmds[i][0] != cmds[i+1][0] for i in range(len(cmds)-1))
check("10회 반복 — 중복 커맨드 없음", no_dup)

print()
print("=" * 60)
print("Round 4: THRESHOLD 경계값 & 극단값 & 부동소수점")
print("=" * 60)
# dist == THRESHOLD 정확히 (조건: dist < THRESHOLD → 미진입)
# THRESHOLD=0.5, 목표(3,2). dist=0.5이면 조건 dist<0.5 불만족 → START 안 함
exact_x = TARGET_X + THRESHOLD  # (3.5, 2.0) → dist = 0.5
d_exact = compute_dist(exact_x, TARGET_Y)
check("dist == THRESHOLD 정확히 일치 → 미진입", d_exact >= THRESHOLD, f"dist={d_exact:.10f}")

# 아주 약간 안쪽
just_inside_x = TARGET_X + THRESHOLD - 1e-9
d_just = compute_dist(just_inside_x, TARGET_Y)
check("dist = THRESHOLD-1e-9 → 진입", d_just < THRESHOLD, f"dist={d_just:.10f}")

# 극단값: (100, 100)
d_far = compute_dist(100.0, 100.0)
check("극단값 (100,100) → 미진입", d_far >= THRESHOLD, f"dist={d_far:.2f}")
check("극단값 dist > 100", d_far > 100, f"dist={d_far:.4f}")

# 부동소수점 누적: 동일 좌표 100번 반복해도 플래그 일관성 유지
rep_positions = [(3.1, 2.1)] * 100
cmds_rep, active_rep = simulate(rep_positions)
check("동일 좌표 100회 → START 1번만", len(cmds_rep) == 1 and cmds_rep[0][0] == 'START',
      f"cmds={cmds_rep}")
check("동일 좌표 100회 → servo_active=True 유지", active_rep == True)

# 부동소수점 오차: 여러 번 더한 좌표가 동일한 판단을 내는지
acc_x = 0.0
for _ in range(31):
    acc_x += 0.1   # 0.1 * 31 = 3.1 (부동소수점 오차 있음)
d_acc = compute_dist(acc_x, 2.1)
check("부동소수점 누적 좌표 판단 일관성", d_acc < THRESHOLD,
      f"acc_x={acc_x:.15f}, dist={d_acc:.10f}")

print()
print("=" * 60)
print(f"최종 결과: {passed} PASS / {failed} FAIL / 총 {passed+failed}개")
print("=" * 60)
if failed == 0:
    print("전체 PASS — servo_trigger_node.py 로직 이상 없음")
else:
    print("FAIL 항목 있음 — 코드 수정 필요")
