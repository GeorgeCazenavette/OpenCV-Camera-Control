#include <Servo.h>
#include <String.h>

Servo pan_servo;
Servo tilt_servo;

const int pan_servo_pin = 13;
const int tilt_servo_pin = 9;
const int pan_right_pin = 7;
const int pan_left_pin = 6;
const int tilt_left_pin = 5;
const int tilt_right_pin = 4;

int pan_vel = 15;
int tilt_vel = 15;

String str;
int velocities[2];


// This function runs one time when the Arduino resets
// It sets up all of the I/O pins and then wait for the python progrma to start
void setup() {
  Serial.begin(9600);
  
  pinMode(pan_servo_pin, OUTPUT);
  pinMode(tilt_servo_pin, OUTPUT);
  
  pinMode(pan_left_pin, INPUT);
  pinMode(pan_right_pin, INPUT);
  pinMode(tilt_left_pin, INPUT);
  pinMode(tilt_right_pin, INPUT);
    
  pan_servo.attach(pan_servo_pin);
  tilt_servo.attach(tilt_servo_pin);
  str = "";
  
  // The Python program sends "scan." on startup
  while (!str.equals("scan"))
  {
    Serial.println(str);
    str = read_string();
  }
}

// This function loops indefinitely after the setup function completes
void loop() {
  scan();
  track();
}


// Scanning function
void scan()
{
  while(1)
  {
    str = read_string();

    // stop scanning if told to track
    if(str.equals("track"))
    {      
      return;
    }

    // Reverse direction when it reaches the limit switch
    if(!panControl(1500 + pan_vel))
    {
      pan_vel = -pan_vel;
      
    }

    // Reverse direction when it reaches the limit switch
    if(!tiltControl(1500 + tilt_vel))
    {
      tilt_vel = -tilt_vel;
    }
  }
}

// Tracking function
void track()
{
  // Initially tell both motors to stop moving
  panControl(1500);
  tiltControl(1500);
  int panVel = 1500;
  int tiltVel = 1500;
  while(1)
  {

    // sets velocities of motors
    panControl(panVel);
    tiltControl(tiltVel);
    
    // reads message from Python program
    str = read_string();
  
    // go back to scanning if the Python program says to
    if(str.equals("scan"))
    {
      return;
    }
    
    
    else
    {
      int index = str.indexOf(',');
  
      // recieved comma seperated valocities
      if(index != -1) {
        // parse them from the input string
        velocities[0] = str.substring(0, index).toInt();
        velocities[1] = str.substring(index+1).toInt();
        // set respective velocities
        panVel = velocities[0];
        tiltVel = velocities[1];
      }
    }
  }
}

// Controls the velocity of the pan motor
boolean panControl(int velocity)
{
  
  // Only set to given speed if doing so would not cause an over rotation
  if((velocity < 1500 && digitalRead(pan_left_pin)) || (velocity >= 1500 && digitalRead(pan_right_pin)))
  {
    pan_servo.writeMicroseconds(velocity);
    return true;
  }

  // If it would cause an over rotation, stop moving and return false
  else
  {
    pan_servo.writeMicroseconds(1500);
    return false;
  }
}

// Controls velocity of the tilt motor
boolean tiltControl(int velocity)
{

  // Only set to given speed if doing so would not cause an over rotation
  if((velocity < 1500 && digitalRead(tilt_left_pin)) || (velocity >= 1500 && digitalRead(tilt_right_pin) ))
  {
    tilt_servo.writeMicroseconds(velocity);
    return true;
  }

  // If it would cause an over rotation, stop moving and return false
  else
  {
    tilt_servo.writeMicroseconds(1500);
    return false;
  }
}

// Function to read string sent from Python program
String read_string()
{
  String input = "";
  char character = ' ';

  // if there is a character to be read
  if (Serial.available())
  {

    // I'm too afraid to change or remove this condition
    while(character != '\n')
    {
      // wait for next character
      while (! Serial.available());
      character = Serial.read();
  
      // Break at the end of message character
      if(character == '.')
      {
        break;
      }
      // add character to the working message
      input += character;
    }
  }

  // return the recieved message or ""
  return input;
}

