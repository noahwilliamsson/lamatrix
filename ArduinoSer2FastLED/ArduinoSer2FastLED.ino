/**
 * Firmware to control a LED matrix display
 * https://github.com/noahwilliamsson/lamatrix
 *
 *   -- noah@hack.se, 2018
 *
 */

#ifdef TEENSYDUINO
#include <TimeLib.h>
#endif
#include "FastLED.h"


#define HOST_SHUTDOWN_PIN 8
#define LEFT_BUTTON_PIN 9
#define RIGHT_BUTTON_PIN 10
#define NUM_LEDS 256

#ifdef TEENSYDUINO
#define FastLED_Pin 6
#else
#define FastLED_Pin 22
#endif


static void put_pixel(int, int, int);
static void render_clock(int);
#ifdef TEENSYDUINO
static time_t getTeensy3Time();
#endif


/**
 * Serial protocol
 */
enum {
  FUNC_RESET = 0,
  /* Initialize display with [pixels & 0xff, (pixels>>8) & 0xff] LEDs */
  FUNC_INIT_DISPLAY = 'i',
  /* Clear display: [dummy byte] */
  FUNC_CLEAR_DISPLAY = 'c',
  /* Update display: [dummy byte] */
  FUNC_SHOW_DISPLAY = 's',
  /* Put pixel at [pixel&0ff, (pixel >> 8) &0xff, R, G, B] */
  FUNC_PUT_PIXEL = 'l',
  /* Set time [t&0xff, (t >> 8) & 0xff, (t >> 16) & 0xff, (t >> 24) & 0xff] */
  FUNC_SET_RTC = '@',
  /* Automatically render time [enable/toggle byte] */
  FUNC_AUTO_TIME = 't',
  /* Suspend host for [seconds & 0xff, (seconds >> 8) & 0xff] */
  FUNC_SUSPEND_HOST = 'S',
};


/* Computed with pixelfont.py */
static int font_width = 4;
static int font_height = 5;
static char font_alphabet[] = " %'-./0123456789:?acdefgiklmnoprstwxy";
static unsigned char font_data[] = "\x00\x00\x50\x24\x51\x66\x00\x00\x60\x00\x00\x00\x42\x24\x11\x57\x55\x27\x23\x72\x47\x17\x77\x64\x74\x55\x47\x74\x71\x74\x17\x57\x77\x44\x44\x57\x57\x77\x75\x74\x20\x20\x30\x24\x20\x52\x57\x25\x15\x25\x53\x55\x73\x31\x71\x17\x13\x71\x71\x75\x27\x22\x57\x35\x55\x11\x11\x57\x77\x55\x75\x77\x75\x55\x75\x57\x17\x71\x35\x55\x17\x47\x77\x22\x22\x55\x77\x55\x25\x55\x55\x27\x02";

/* Global states */
int state = 0;
int debug_serial = 0;
/* Debug state issues */
int last_states[8];
unsigned int last_state_counter = 0;
/* Non-zero when automatically rendering the current time */
int show_time = 1;
/* Non-zero while the host computer is turned off */
time_t reboot_at = 0;
/* Accumulator register for use between loop() calls */
unsigned int acc;
unsigned int color;
CRGB leds[NUM_LEDS];


static volatile int g_button_state;
static int button_down_t;
static void button_irq_left(void) {
  int state = digitalRead(LEFT_BUTTON_PIN);

  if(state == HIGH) {
    /* Start counting when the circuit is broken */
    button_down_t = millis();
    return;
  }
  if(!button_down_t)
    return;

  int pressed_for_ms = millis() - button_down_t;
  if(pressed_for_ms > 1500)
    g_button_state = 4;
  else if(pressed_for_ms > 500)
    g_button_state = 2;
  else if(pressed_for_ms > 100)
    g_button_state = 1;

  button_down_t = 0;
}

static void button_irq_right(void) {
  int state = digitalRead(RIGHT_BUTTON_PIN);

  if(state == HIGH) {
    /* Start counting when the circuit is broken */
    button_down_t = millis();
    return;
  }
  if(!button_down_t)
    return;

  int pressed_for_ms = millis() - button_down_t;
  if(pressed_for_ms > 1500)
    g_button_state = 64;
  else if(pressed_for_ms > 500)
    g_button_state = 32;
  else if(pressed_for_ms > 100)
    g_button_state = 16;

  button_down_t = 0;
}


void setup() {
  Serial.begin(460800);

  /* Initialize FastLED library */
  FastLED.addLeds<NEOPIXEL, FastLED_Pin>(leds, NUM_LEDS);

  /* Configure pin used to shutdown Raspberry Pi (connected to GPIO5 on the Pi) */
  pinMode(HOST_SHUTDOWN_PIN, OUTPUT);
  digitalWrite(HOST_SHUTDOWN_PIN, HIGH);

  /* Configure pins for the buttons */
  pinMode(LEFT_BUTTON_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(LEFT_BUTTON_PIN), button_irq_left, CHANGE);
  pinMode(RIGHT_BUTTON_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(RIGHT_BUTTON_PIN), button_irq_right, CHANGE);

#ifdef TEENSYDUINO
  /* Initialize time library */
  setSyncProvider(getTeensy3Time);
  if (timeStatus() != timeSet) {
     Serial.println("Unable to sync with the RTC");
  }
  else {
     Serial.println("RTC has set the system time");
     show_time = 1;
  }
  Serial.printf("%04d-%02d-%02dT%02d:%02d:%02dZ\n", year(), month(), day(), hour(), minute(), second());
#endif
}


void loop() {
#ifdef TEENSYDUINO
  time_t now = getTeensy3Time();
#else
  int now = 0;
#endif

  int button_state = g_button_state;
  if(button_state) {
    g_button_state = 0;

    if(button_state & 1)
      Serial.println("LEFT_SHRT_PRESS");
    else if(button_state & 2)
      Serial.println("LEFT_LONG_PRESS");
    else if(button_state & 4)
      Serial.println("LEFT_HOLD_PRESS");
    if(button_state & 16)
      Serial.println("RGHT_SHRT_PRESS");
    else if(button_state & 32)
      Serial.println("RGHT_LONG_PRESS");
    else if(button_state & 64)
      Serial.println("RGHT_HOLD_PRESS");
  }

  if(reboot_at && now >= reboot_at) {
    /* Restart host computer */
    digitalWrite(HOST_SHUTDOWN_PIN, LOW);
    delay(1);
    digitalWrite(HOST_SHUTDOWN_PIN, HIGH);
    reboot_at = 0;
  }

  if(show_time) {
    /* Automatically render time */
    if(show_time != now || button_state) {
      render_clock(button_state);
      show_time = now;
    }
  }

  if (Serial.available() <= 0) return;
  int val = Serial.read();
  last_states[last_state_counter++ % (sizeof(last_states)/sizeof(last_states[0]))] = val;
  switch(state) {
  case FUNC_RESET:
    /**
     * Pyserial sometimes experience write timeouts so we
     * use a string of zeroes to resynchronize the state.
     */
    state = val;
    break;

  case FUNC_INIT_DISPLAY:
    acc = val;
    state++;
    break;
  case FUNC_INIT_DISPLAY+1:
    acc |= val << 8;
    FastLED.addLeds<NEOPIXEL, FastLED_Pin>(leds, acc);
    /* fall through */

  case FUNC_SET_RTC:
    acc = val;
    state++;
    break;
  case FUNC_SET_RTC+1:
    acc |= val << 8;
    state++;
    break;
  case FUNC_SET_RTC+2:
    acc |= val << 16;
    state++;
    break;
  case FUNC_SET_RTC+3:
    acc |= val << 24;
#ifdef TEENSYDUINO
    Teensy3Clock.set(acc); // set the RTC
    setTime(acc);
    Serial.printf("RTC synchronized: %04d-%02d-%02dT%02d:%02d:%02dZ\n", year(), month(), day(), hour(), minute(), second());
#endif
    state = FUNC_RESET;
    break;

  case FUNC_CLEAR_DISPLAY:
    for(int i = 0; i < NUM_LEDS; i++)
      leds[i].setRGB(0,0,0);
    /* fall through */

  case FUNC_SHOW_DISPLAY:
    FastLED.show();
    state = FUNC_RESET;
    break;

  case FUNC_SUSPEND_HOST:
    acc = val;
    state++;
    break;
  case FUNC_SUSPEND_HOST+1:
    acc |= val << 8;
    /* TODO: Suspend host computer */
    reboot_at = now + acc;
    if(reboot_at >= 10) {
      /* Automatically render time while host computer is offline */
      show_time = 1;
      Serial.printf("Shutting down host computer, reboot scheduled in %ds\n", reboot_at);
      /* Initiate poweroff on Raspberry Pi */
      digitalWrite(HOST_SHUTDOWN_PIN, LOW);
      delay(1);
      digitalWrite(HOST_SHUTDOWN_PIN, HIGH);
    }

    state = FUNC_RESET;
    break;

  case FUNC_AUTO_TIME:
    if(val == '\r' || val == '\n')
      show_time = !show_time; /* toggle */
    else
      show_time = val;

    /* Clear display */
    for(int i = 0; i < NUM_LEDS; i++)
      leds[i].setRGB(0,0,0);
    FastLED.show();

    Serial.printf("Automatic rendering of current time: %d\n", show_time);
    state = FUNC_RESET;
    break;

  case FUNC_PUT_PIXEL:
    acc = val;
    state++;
    break;
  case FUNC_PUT_PIXEL+1:
    acc |= val << 8;
    state++;
    break;
  case FUNC_PUT_PIXEL+2:
    color = val;
    state++;
    break;
  case FUNC_PUT_PIXEL+3:
    color |= val << 8;
    state++;
    break;
  case FUNC_PUT_PIXEL+4:
    color |= val << 16;
    leds[(acc % NUM_LEDS)].setRGB(color & 0xff, (color >> 8) & 0xff, (color >> 16) & 0xff);
    state = FUNC_RESET;
    break;

  default:
    Serial.printf("Unknown func %d with val %d, resetting\n", state, val);
    for(unsigned int i = 0; i < sizeof(last_states)/sizeof(last_states[0]) && last_state_counter - i > 0; i++)
      Serial.printf("Previous state %d: %d\n", i, last_states[(last_state_counter-i) % (sizeof(last_states)/sizeof(last_states[0]))]);
    state = FUNC_RESET;
    break;
  }
}


/* Pretty much a port of LedMatrix.xy_to_phys() */
static void put_pixel(int x, int y, int lit) {
  /** 
   * The LEDs are laid out in a long string going from north to south,
   * one step to the east, and then south to north, before the cycle
   * starts over
   */
  int cycle = 16;
  int nssn_block = x / 2;
  int phys_addr = nssn_block * 16;
  int brightness_scaler = 48;  /* use less power */

  if(x % 2)
    phys_addr += cycle - 1 - y;
  else
    phys_addr += y;

  lit &= 0xff;
  lit /= brightness_scaler;
  leds[phys_addr % NUM_LEDS].setRGB(lit, lit, lit);
}


#ifdef TEENSYDUINO
/* Wrapper function for Timelib's sync provider */
static time_t getTeensy3Time(void)
{
  return Teensy3Clock.get();
}
#endif


/* Render time as reported by the RTC */
static int clock_state = 0x2;
static void render_clock(int button_state) {
  char buf[10];
  int x_off;
  size_t len;

  if(button_state) {
    clock_state ^= 1 << (button_state-1);
    for(int i = 0; i < NUM_LEDS; i++)
      leds[i].setRGB(0,0,0);
  }

#ifdef TEENSYDUINO
  if((clock_state & 1) == 0) {
      sprintf(buf, "%02d:%02d", hour(), minute());
      if((clock_state & 2) && second() % 2)
          buf[2] = ' ';
  }
  else {
      sprintf(buf, "%02d.%02d.%02d", day(), month(), year() % 100);
  }
#else
  sprintf(buf, "00:00");
#endif

  if((clock_state & 1) == 0)
      x_off = 8 - clock_state;
  else
      x_off = 2;

  len = strlen(buf);
  for(size_t i = 0; i < len; i++) {
    unsigned char digit = buf[i];
    size_t offset;

    /* Kludge to compress colons and dots to two columns */
    if(digit == ':' || digit == '.' || digit == ' ' || (i && (buf[i-1] == ':' || buf[i-1] == '.' || buf[i-1] == ' ')))
      x_off--;

    for(offset = 0; offset < strlen(font_alphabet); offset++) {
      if(font_alphabet[offset] == digit) break;
    }

    int font_byte = (offset * font_width * font_height) / 8;
    int font_bit = (offset * font_width * font_height) % 8;
    for(int y = 0; y < font_height; y++) {
      for(int x = 0; x < font_width; x++) {
        if(font_data[font_byte] & (1<<font_bit))
          put_pixel(x_off+x, y, 255);
        else
          put_pixel(x_off+x, y, 0);

        if(++font_bit == 8) {
          font_byte++;
          font_bit = 0;
        }
      }
    }

    x_off += font_width;
  }

#ifdef TEENSYDUINO
  /* Display seconds bar */
  if(clock_state == 2) {
    int height = 1 + second() / 12;
    for(int y = 0; y < 5; y++) {
      int color = 0;
      if(y < height) color = 128;
      if(y == height-1 && second() % 2) color = 0;
      put_pixel(x_off+1, 4-y, color);
    }
  }

  /* Display weekdays */
  x_off = 2;
  int today_to_i = (weekday() + 5) % 7;
  for(int i = 0; i < 7; i++) {
    int color = i == today_to_i? 255: 64;
    put_pixel(x_off+4*i+0, 7, color);
    put_pixel(x_off+4*i+1, 7, color);
    put_pixel(x_off+4*i+2, 7, color);
  }
#endif

  FastLED.show();
}
