# Work: Project 6 — Gesture (手势触发器)

来源: https://yidanxu.webflow.io/work/project-6

---

HOME
ABOUT ME
PROJECT
PRESS

GESTURE
AI · Machine learning · Gesture recognition · Arduino

## Project Overview
This is a device for a new approach to password exploration. It features a smart lock structure that uses machine learning to recognize gestures. Each small circular ring corresponds to the angle of a finger and is controlled by a small servo motor. When all the gestures are correct, the door lock will open.

## My Contributions
- Connection and Testing with Arduino
- Responsible for Visual Structure Design
- Responsible for Laser Cutting
- Responsible for training machine learning

This device consists of four SG92R micro servos, one MG996R servo, one MG995R servo, and an Arduino.

The machine learning part uses Vision OSC connected to Wekinator. The design logic is that each gesture corresponds to a circle, and the rotation angle of the gesture controls the actual rotation of the small circle. When all four gestures are rotated to the specified angle, the iris structure will rotate and open, and the internal push rod will push out the locked item.

## Design Point — process of technical implementation: gesture and angle design

**Vision OSC** — Input hand signals, use VisionOSC to recognize hand gestures, and output signals to processing.

**Processing** — Using processing to collect messages and convert them into binary signals that can be analyzed by wekinator.

**Wekinator** — Machine learning is performed by analyzing electrical signals from processing.
- classification, identify various gestures
- custom, identify the exact degree of rotation.

**Arduino** — Two different signals are received through processing and output to Arduino, and Arduino can control the precise rotation of a specific steering machine according to gestures and rotation degrees to achieve mechanical control.

## Process Of Technical Implementation — Hardware
- **SG92R** — Control the motion of the disc and connecting rod
- **MG996R** — It can be rotated 360 times, it is used to control the opening and closing of the iris structure
- **MG995R** — Control the movement of the telescopic structure

## Process Of Technical Implementation — Structure

### Coding 01 — Vision OSC → Processing (VisionOSC connect demo created by Revive / Weiqi Sun)
```processing
import oscP5.*;
import netP5.*;
NetAddress wekinatorAddress;
OscP5 oscP5;
int HAND_N_PART = 21;
int MAX_DET = 32;
class KeyPt {
  float x; float y; float score;
  KeyPt(float _x, float _y, float _score) { x = _x; y = _y; score = _score; }
}
class PtsDetection {
  float score; KeyPt[] points;
  PtsDetection(int n) { points = new KeyPt[n]; }
}
PtsDetection[] hands;
int nHand = 0; int vidW; int vidH;
void setup() {
  size(640, 480);
  oscP5 = new OscP5(this, 59183);
  wekinatorAddress = new NetAddress("127.0.0.1", 6448); // Change to your Wekinator address and port
  hands = new PtsDetection[MAX_DET];
}
void draw() {
  background(0);
  fill(0, 255, 255);
  drawPtsDetection(hands, nHand, 5);
  fill(255);
}
void drawPtsDetection(PtsDetection[] dets, int nDet, int rad) {
  pushStyle(); noStroke();
  for (int i = 0; i < nDet; i++) {
    for (int j = 0; j < dets[i].points.length; j++) {
      if (dets[i].points[j] != null) { circle(dets[i].points[j].x, dets[i].points[j].y, rad); }
    }
  }
  popStyle();
}
int readPtsDetection(OscMessage msg, int nParts, PtsDetection[] out) {
  vidW = msg.get(0).intValue();
  vidH = msg.get(1).intValue();
  int nDet = msg.get(2).intValue();
  int n = nParts * 3 + 1;
  for (int i = 0; i < nDet; i++) {
    PtsDetection det = new PtsDetection(nParts);
    det.score = msg.get(3 + i * n).floatValue();
    for (int j = 0; j < nParts; j++) {
      float x = msg.get(3 + i * n + 1 + j * 3).floatValue();
      float y = msg.get(3 + i * n + 1 + j * 3 + 1).floatValue();
      float score = msg.get(3 + i * n + 1 + j * 3 + 2).floatValue();
      det.points[j] = new KeyPt(x, y, score);
    }
    out[i] = det;
  }
  return nDet;
}
void oscEvent(OscMessage msg) {
  if (msg.addrPattern().equals("/hands/arr")) {
    nHand = readPtsDetection(msg, HAND_N_PART, hands);
    OscMessage wekinatorMsg = new OscMessage("/wek/inputs");
    for (int i = 0; i < nHand; i++) {
      for (int j = 0; j < HAND_N_PART; j++) {
        if (hands[i].points[j] != null) {
          float relativeX = hands[i].points[j].x / vidW;
          float relativeY = hands[i].points[j].y / vidH;
          wekinatorMsg.add(relativeX);
          wekinatorMsg.add(relativeY);
        }
      }
    }
    oscP5.send(wekinatorMsg, wekinatorAddress);
  }
}
```

### Coding 02 — Processing / Wekinator → Arduino
```arduino
#include "PCA9685.h"
#include <Wire.h>
ServoDriver servo;
const int servoR1Pin = 1;
const int servoR2Pin = 2;
const int servoR3Pin = 3;
const int servoR4Pin = 4;
const int servoDoorPin = 5;
const int servoR6Pin = 6;
const int minValidAngle = 20;
const int maxValidAngle = 180;
int currentAngleR1 = 90;
int currentAngleR2 = 90;
int currentAngleR3 = 90;
int currentAngleR4 = 90;
int currentAngleDoor = 90;
int currentAngleR6 = 90;
void setup() {
  Wire.begin();
  Serial.begin(9600);
  servo.init(0x7f);
}
void loop() {
  static bool servoDoorMoved = false;
  if (Serial.available() >= 4) {
    char classification = Serial.read();
    int angle = 0;
    for (int i = 0; i < 3; i++) {
      char digit = Serial.read();
      if (digit >= '0' && digit <= '9') { angle = angle * 10 + (digit - '0'); }
      else { Serial.println("Error"); return; }
    }
    if (classification >= '1' && classification <= '5' && angle >= 0 && angle <= 180) {
      switch (classification) {
        case '1': servo.setAngle(servoR1Pin, angle); break;
        case '2': servo.setAngle(servoR2Pin, angle); break;
        case '3': servo.setAngle(servoR3Pin, angle); break;
        case '4': servo.setAngle(servoR4Pin, angle); break;
        case '5':
          if (!servoDoorMoved) {
            if (currentAngleR1 >= minValidAngle && currentAngleR1 <= maxValidAngle &&
                currentAngleR2 >= minValidAngle && currentAngleR2 <= maxValidAngle &&
                currentAngleR3 >= minValidAngle && currentAngleR3 <= maxValidAngle &&
                currentAngleR4 >= minValidAngle && currentAngleR4 <= maxValidAngle) {
              servo.setAngle(servoDoorPin, 180);
              delay(5000);
              servo.setAngle(servoR6Pin, 179);
              delay(2000);
              servo.setAngle(servoR6Pin, 90);
              servoDoorMoved = true;
              Serial.println("classifiers " + String(classification) + "，angle：" + String(angle));
            } else {
              Serial.println("Error: servoR1, servoR2, servoR3, and servoR4 angles not in the valid range.");
            }
          }
          break;
      }
    } else {
      Serial.println("Error");
    }
  }
}
```

### Coding 03 — Processing / Wekinator (forwarding to Arduino)
```processing
import processing.serial.*;
import oscP5.*;
import netP5.*;
int receivedInteger;
Serial arduino;
OscP5 oscP5;
public int classificationSignal;
public int angle;
int outputInterval = 1000;
int lastOutputTime = 0;
void setup() {
  size(600, 300);
  oscP5 = new OscP5(this, 12000);
  String arduinoPort = "/dev/cu.usbmodem141201";
  arduino = new Serial(this, arduinoPort, 9600);
}
void draw() {
  background(0);
  text("Forwarding Wekinator messages to Arduino...", 50, 30);
}
void sendArduinoData(int classificationSignal, int angle) {
  classificationSignal = constrain(classificationSignal, 0, 9);
  String formattedAngle = String.format("%03d", angle);
  String formattedData = classificationSignal + formattedAngle;
  arduino.write(formattedData);
  println("Received OSC Signal: Classification=" + classificationSignal + ", Angle=" + formattedAngle);
}
void oscEvent(OscMessage msg) {
  if (msg.checkAddrPattern("/wek/outputs")) {
    float value1 = msg.get(0).floatValue();
    float value2 = msg.get(1).floatValue();
    classificationSignal = int(value1);
    angle = int(value2);
    String formattedAngle = String.format("%03d", angle);
    println("Received OSC Signal: Classification=" + classificationSignal + ", Angle=" + formattedAngle);
    int currentTime = millis();
    if (currentTime - lastOutputTime >= outputInterval) {
      sendArduinoData(classificationSignal, angle);
      lastOutputTime = currentTime;
    }
  }
}
```

---

POWERED BY WEBFLOW
EMAIL
LINKEDLN
