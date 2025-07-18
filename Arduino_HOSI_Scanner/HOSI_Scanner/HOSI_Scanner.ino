/*

_________________________HOSI Arduino Firmware_____________________________

 Manual control:
 The HOSI can be controlled automatically by the HOSI_GUI Python software. however, the functions can
 also be accessed manually via a serial port (check the baud, default 115200)
 
 tilt: send "l" followed by a number e.g. "l100" or "l500" note that zero is straight down, do not use negative values
 pan: send "p" followed by a number e.g. "p100" or "p-1000" note that zero is straight ahead
 manual integration time: send "t" followed by microsecond number
 radiance measurement: send "r" and it will take a radiance measurement
 shutter control: send "open" to open shutter, "close" to close shutter, "shutter" to report status
 hyperspectral measurement: send "h" followed by comma-delineated values as follows:
 panLeft,panRight,panResolution,tiltBottom,tiltTop,tiltResolution,maxIntegrationTime(microseconds),boxcar,darkRepeatTimer(milliseconds)
 e.g.: "h-200,200,10,400,600,10,2000000,2,120000"
  
 
 Modify the unit number below if desired, and upload this script to an Arduino Nano or similar.
 
 
 */


#include <AccelStepper.h>
#include <Servo.h>


int unitNumber = 9;

// Spectrometer pins
#define TRGpin A0
#define STpin A1
#define CLKpin A2
#define VIDEOpin A3

// Pan Motor (Motor 1)
#define PAN_IN1 2
#define PAN_IN2 3
#define PAN_IN3 4
#define PAN_IN4 5

// Roll Motor (Motor 2)
#define ROLL_IN1 6
#define ROLL_IN2 7
#define ROLL_IN3 8
#define ROLL_IN4 9

#define nSites 288 // 
uint16_t data[nSites] [2];
int dataLoc = 0;

int delayTime = 1;
long intTime = 100;
long prevIntTime = 100;
long maxIntTime = 3000000; // maximum integration time for auto & manual measurement milliseconds
int minIntTime = 50; //the sensor doesn't work below a certain numebr of scans... it needs three cycles with the ST pin high, even then you need to add about 378 microseconds to the exposure
int intStep = 400;
long manIntTime = 0;
int satN = 0; // number of bands over-exposed
int prevSatN = 0;
int satVal = 998; // over-exposure value
int baudrate = 115200;

int panoSteps[] = {913, 959, 988, 1005};
int panoSpaces[] = {2, 4, 8, 16};

long hyperVals[9];
long panVal = 0;
long tiltVal = 0;
int darkLight = 1; // 0= dark measurement, 1=light measurement
long darkRepeat = 30000;// repeat dark measurement every few seconds/minutes

// Add stop flag for interrupting operations
bool stopRequested = false;

AccelStepper stepper_pan(4, PAN_IN1, PAN_IN3, PAN_IN2, PAN_IN4); // 8=HALF4WIRE, then input pin 1, 2, 3, 4
AccelStepper stepper_tilt(4, ROLL_IN1, ROLL_IN3, ROLL_IN2, ROLL_IN4); // 8=HALF4WIRE, then input pin 1, 2, 3, 4

// Initialize servo for dark measurement shutter
Servo shutterServo;
bool isShutterOpen = false;

int boxcar = 1;

// Servo pin for dark measurement shutter
#define SERVO_PIN 10

// Shutter positions
#define SHUTTER_CLOSED 100
#define SHUTTER_OPEN 130

void setup() {
  stepper_pan.setMaxSpeed(500.0); // 800 for half-step
  stepper_pan.setAcceleration(5000.0);
  stepper_pan.disableOutputs();

  stepper_tilt.setMaxSpeed(500.0);
  stepper_tilt.setAcceleration(5000.0);  
  stepper_tilt.disableOutputs();
  
  // Initialize shutter servo and close it
  shutterServo.attach(SERVO_PIN);
  closeShutter();
      
  //Set desired pins to OUTPUT
  pinMode(CLKpin, OUTPUT);
  pinMode(STpin, OUTPUT);

  digitalWrite(CLKpin, HIGH);
  digitalWrite(STpin, LOW);

  Serial.begin(baudrate);
  while (! Serial); // Wait untilSerial is ready
  readSpectrometer();
  resetData();
  
}

void readSpectrometer(){

  // Start clock cycle and set start pulse to signal start
  digitalWrite(CLKpin, LOW);
  delayMicroseconds(delayTime);
  digitalWrite(CLKpin, HIGH);
  delayMicroseconds(delayTime);
  digitalWrite(CLKpin, LOW);
  digitalWrite(STpin, HIGH);
  delayMicroseconds(delayTime);

  // microseconds
     unsigned long cTime = micros(); // start time
     unsigned long eTime = cTime + intTime; // end time
  
  //Sample for a period of time
 // for(int i = 0; i < 15; i++){ //orig 15
     while(cTime < eTime){
         digitalWrite(CLKpin, HIGH);
         delayMicroseconds(delayTime);
         digitalWrite(CLKpin, LOW);
         delayMicroseconds(delayTime);
         cTime=micros();
      } 

  //Set STpin to low
  digitalWrite(STpin, LOW);

  //Sample for a period of time
  for(int i = 0; i < 88; i++){ //87 aligns correctly

      digitalWrite(CLKpin, HIGH);
      delayMicroseconds(delayTime);
      digitalWrite(CLKpin, LOW);
      delayMicroseconds(delayTime); 
      
  }

  int specRead = 0;
  satN = 0;
  for(int i = 0; i < nSites; i++){

      specRead = analogRead(VIDEOpin);
      // second read shoudl stablise the multiplexer and give more accurate read
      //delayMicroseconds(delayTime);
     // specRead = analogRead(VIDEOpin);
      data[i][dataLoc] += specRead;
      if(specRead > satVal)
        satN ++;
      
      digitalWrite(CLKpin, HIGH);
      delayMicroseconds(delayTime);
      digitalWrite(CLKpin, LOW);
      delayMicroseconds(delayTime);
        
  } 
}


void resetData(){
  for (int i = 0; i < nSites; i++)
    data[i][dataLoc] = 0;
}

void switchDim(){
  if(dataLoc == 0)
    dataLoc = 1;
  else
    dataLoc = 0;
}

void radianceMeasure(){

  // reset all data
  dataLoc = 1;
  resetData();
  dataLoc = 0;
  resetData();

  // ----------------- AUTO EXPOSURE-----------
  if(manIntTime == 0){ 
    intTime = minIntTime; // microsecond exposure
    readSpectrometer(); // read to dim0
    //data[0][dataLoc] = -1; // debugging
    prevSatN = satN;
    prevIntTime = intTime;
    intTime = intStep;
    if(satN > 0)
      switchDim(); // required if first exposure is over-exposed

    while(satN == 0 && intTime < maxIntTime){
      switchDim();
      resetData();
      readSpectrometer();
      //data[0][dataLoc] = intTime;// debugging

      if(satN == 0){
        prevSatN = satN;
        prevIntTime = intTime;
        intTime = intTime*2;
      }

    } //while

    //if(prevIntTime > -1) // if first exposure isn't over-exposed
      switchDim(); 
      
  //------------- MANUAL EXPOSURE-------------
  } else { 
    intTime = manIntTime;
    readSpectrometer(); // read to dim0
    prevSatN = satN;
    prevIntTime = intTime;
  }
 
  Serial.print(String(panVal) + "," + String(tiltVal) + "," + String(darkLight) + "," + String(prevIntTime) + "," + String(prevSatN) );

  for (int i = 0; i < nSites; i+=boxcar){
    int tSum = 0;
    for(int j = 0; j < boxcar; j++)
      if(i+j <= nSites)
          tSum += data[i+j][dataLoc];
    Serial.print("," + String(tSum));
  }
  Serial.print("\n");
  delay(1);
 
}


void pan(long pv){
  //stepper_pan.enableOutputs();
  stepper_pan.runToNewPosition(pv);
  //stepper_pan.disableOutputs();
}

void tilt(long tv){
  //stepper_tilt.enableOutputs();
  stepper_tilt.runToNewPosition(tv);
  //stepper_tilt.disableOutputs();
}

// Shutter control functions
void openShutter(){
  shutterServo.write(SHUTTER_OPEN);
  isShutterOpen = true;
  // Serial.println("Shutter opened");
  delay(100); // Give the servo time to move
}

void closeShutter(){
  shutterServo.write(SHUTTER_CLOSED);
  isShutterOpen = false;
  // Serial.println("Shutter closed");
  delay(100); // Give the servo time to move
}

void reportShutterStatus(){
  Serial.print("Shutter is ");
  Serial.println(isShutterOpen ? "OPEN" : "CLOSED");
  Serial.print("Servo angle: ");
  Serial.println(isShutterOpen ? SHUTTER_OPEN : SHUTTER_CLOSED);
}

// Add servo control function
void setServoAngle(int angle){
  shutterServo.write(angle);
  Serial.println("Servo angle set to: " + String(angle));
  delay(100); // Give the servo time to move
}

void darkMeasure(){
      //-----------Close shutter for dark measurement------------
      closeShutter();
      darkLight = 0; // dark measurement
      long tl = manIntTime; // save existing manual value

      // first scan at microsecond
      manIntTime = minIntTime;
      radianceMeasure();
   
      for (long i = intStep; i <= maxIntTime; i*= 2){
        if(stopRequested) return; // Check for stop request
        manIntTime = i;
        radianceMeasure();
      }

      //-----------Open shutter for light measurement------------
      openShutter();
      manIntTime = tl;// restore manIntTime
      darkLight = 1; // light measurement
}

void startMeasure(){
      //-----------Return to zero point------------
      //panVal = 0;
      pan(0);
      //tilt(512);  // Commented out to prevent unwanted tilt movement
      
      //-----------Close shutter for initial dark measurement------------
      closeShutter();
      darkLight = 2; // dark measurement
      radianceMeasure();
      
      //-----------Open shutter for light measurement------------
      openShutter();
      darkLight = 1; // light measurement
}


void loop() {

  
  String arg = Serial.readString();

  if (arg != NULL){

    // Stop command - interrupt any ongoing operation
    if(arg == "stop"){
      stopRequested = true;
      Serial.println("Stop requested");
      
      // Return to origin and close shutter when stopping
      stepper_pan.enableOutputs();
      stepper_tilt.enableOutputs();
      pan(0);  // Return pan to origin
      tilt(0); // Return tilt to origin
      closeShutter(); // Close shutter
      stepper_pan.disableOutputs();
      stepper_tilt.disableOutputs();
      
      Serial.println("Returned to origin and closed shutter");
      return;
    }

    // manually set integration time
    if(arg.startsWith("t") == true){
      arg.replace("t", "");
      manIntTime = (long) arg.toFloat();
      if(manIntTime > maxIntTime)
          manIntTime = maxIntTime;
      Serial.println("int. time: " + String(manIntTime) + "ms");

    // manual pan
    } else if(arg.startsWith("p") == true){
      arg.replace("p", "");
      stepper_pan.enableOutputs();
      pan((int) arg.toFloat());
      stepper_pan.disableOutputs();
      Serial.println("pan: " + String((int) arg.toFloat()));
      delay(5);

    // manual tilt
    } else if(arg.startsWith("l") == true){
      arg.replace("l", "");
      stepper_tilt.enableOutputs();
      tilt((int) arg.toFloat());
      stepper_tilt.disableOutputs();
      Serial.println("tilt: " + String((int) arg.toFloat()));
      delay(5);

    // Manual servo control
    } else if(arg.startsWith("s") == true){
      arg.replace("s", "");
      int angle = (int) arg.toFloat();
      if(angle >= 0 && angle <= 180){
        setServoAngle(angle);
      } else {
        Serial.println("Invalid servo angle (0-180)");
      }

    // Manual spec measure
    } else if(arg.startsWith("r") == true){ // radiance

      radianceMeasure();

    // Manual shutter control
    } else if(arg == "open"){
      openShutter();
    } else if(arg == "close"){
      closeShutter();
    } else if(arg == "shutter"){
      reportShutterStatus();

    // -------------  hyperspec --------------
    } else if(arg.startsWith("h") == true){
      stopRequested = false; // Reset stop flag at start of new scan
      arg.replace("h", "");
      int i= 0;
      while(arg.indexOf(",") != -1){
        hyperVals[i] = long(arg.substring(0,arg.indexOf(",")).toFloat()); //toInt for int, atol for long
        i++;
        arg = arg.substring(arg.indexOf(",")+1);
      }

   

      Serial.println("h," + String(unitNumber) + "," + String(hyperVals[0]) + "," + String(hyperVals[1]) + "," + String(hyperVals[2]) + "," + String(hyperVals[3]) + "," + String(hyperVals[4]) + "," + String(hyperVals[5]) + "," + String(hyperVals[6]) + "," + String(hyperVals[7]) + "," + String(hyperVals[8]) );
      delay(5);
      //arg = Serial.readString();
      
      maxIntTime = (long) hyperVals[6];
      boxcar = (int) hyperVals[7];
      darkRepeat = (long) hyperVals[8];

      stepper_pan.enableOutputs();
      stepper_tilt.enableOutputs();
      //panVal = 0;
      pan(0);
      //tilt(0);  // Commented out to prevent unwanted tilt movement

      //-----------Dark Measure at start------------
      startMeasure();
      if(stopRequested) {
        // Return to origin and close shutter when stopped early
        pan(0);  // Return pan to origin
        tilt(0); // Return tilt to origin
        closeShutter(); // Close shutter
        Serial.println("x");
        stepper_pan.disableOutputs();
        stepper_tilt.disableOutputs();
        Serial.println("Scan stopped early - returned to origin and closed shutter");
        return;
      }
      darkMeasure();

      unsigned long cDR = millis(); // current time dark repeat
      unsigned long eDR = cDR + darkRepeat; // end time dark repeat
      
      for(tiltVal = hyperVals[3]; tiltVal <= hyperVals[4]; tiltVal += hyperVals[5]){
        if(stopRequested) break; // Check for stop request
        
        // Check for stop command during scanning
        if(Serial.available()) {
          String stopCmd = Serial.readString();
          if(stopCmd == "stop") {
            stopRequested = true;
            break;
          }
        }
        
        //----------repeat dark measurement based on timeout-----------
        cDR = millis();
        if(cDR >= eDR){
            darkMeasure();
            if(stopRequested) break; // Check for stop request after dark measure
            //tilt(tiltVal);
            cDR = millis();
            eDR = cDR + darkRepeat;
        }

        tilt(tiltVal);
        pan(hyperVals[0]-10);// overshoot - pan left a bit to use up excess in gears

        //--------reduce measurement frequency at high elevations
        int panShift = 1;
        int panStart = 0;
        for(int i=0; i<4; i++)
        if(tiltVal >= panoSteps[i]){
            panShift = panoSpaces[i];
            panStart = panoSpaces[i]/2;
        }
        panShift *= hyperVals[2];
        panStart *= hyperVals[2];
          
          //----------pan from left to right-----------
          for(panVal = hyperVals[0]+panStart; panVal <= hyperVals[1]; panVal += panShift){ 
            if(stopRequested) break; // Check for stop request
            
            // Check for stop command during panning
            if(Serial.available()) {
              String stopCmd = Serial.readString();
              if(stopCmd == "stop") {
                stopRequested = true;
                break;
              }
            }
            
            pan(panVal);
            radianceMeasure();
          }
        //}

      }


      //-----------Dark Measure at end------------
      if(!stopRequested) {
        pan(0);
        darkMeasure();
      }

      // Always return to origin and close shutter at end of scan
      pan(0);  // Return pan to origin
      tilt(0); // Return tilt to origin
      closeShutter(); // Close shutter
      
      stepper_pan.disableOutputs();
      stepper_tilt.disableOutputs();

      Serial.println("x");
      Serial.println("Scan completed - returned to origin and closed shutter");
//      Serial.println("\n"); // signal end
    }
  }

  delay(10);  
     
}
