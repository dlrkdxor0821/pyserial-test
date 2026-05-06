#include <Servo.h>

Servo myServo;
const int SERVO_PIN = 9;

void setup() {
  Serial.begin(9600);
  myServo.attach(SERVO_PIN);
  myServo.write(90);  // 정면(CENTER)
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "LEFT") {
      myServo.write(0);    // 왼쪽 90°
    } else if (cmd == "RIGHT") {
      myServo.write(180);  // 오른쪽 180°
    } else if (cmd == "CENTER") {
      myServo.write(90);   // 정면 복귀
    }
  }
}
