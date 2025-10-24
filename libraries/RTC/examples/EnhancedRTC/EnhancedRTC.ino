#include "RTC.h"

ArduinoRTC rtc;

// 7-segment style representation for digits 0–9 and colon ":"
const char* bigDigits[11][3] = {
    {" _ ", "| |", "|_|"}, // 0
    {"   ", "  |", "  |"}, // 1
    {" _ ", " _|", "|_ "}, // 2
    {" _ ", " _|", " _|"}, // 3
    {"   ", "|_|", "  |"}, // 4
    {" _ ", "|_ ", " _|"}, // 5
    {" _ ", "|_ ", "|_|"}, // 6
    {" _ ", "  |", "  |"}, // 7
    {" _ ", "|_|", "|_|"}, // 8
    {" _ ", "|_|", " _|"}, // 9
    {"   ", " . ", " . "}  // colon ":"
};

void printBigTime(int h, int m, int s) {
    // Format time as HH:MM:SS string
    char timeStr[9];
    memset(timeStr, 0, sizeof(timeStr));
    char bigDigitsPrint[40];
    memset(bigDigitsPrint, 0, sizeof(bigDigitsPrint));
    snprintf(timeStr, sizeof(timeStr), "%02d:%02d:%02d", h, m, s); // This (and further such manipulations) is necessary because Serial.print() does not support formatted output like printf()
    Serial.println(timeStr);


    // Print each of the 3 lines row by row
    for (int row = 0; row < 3; row++) {
        for (int i = 0; timeStr[i] != '\0'; i++) {
            char c = timeStr[i];
            if (c >= '0' && c <= '9') {
                sprintf(bigDigitsPrint, "%s ", bigDigits[c - '0'][row]);
                Serial.print(bigDigitsPrint);
            } else if (c == ':') {
                sprintf(bigDigitsPrint, "%s ", bigDigits[10][row]);
                Serial.print(bigDigitsPrint);
            } else {
                Serial.print("    "); // Space or unknown
            }
        }
        Serial.println();
    }
     Serial.println();
}

void setup() {
    Serial.begin(115200);
    rtc.begin();
    bool status = rtc.setTime(2025, 9, 25, 7, 46, 0);  // Initial time
}

void loop() {
    int y, m, d, h, min, s;
    char printBuffer[60]; 
    int status = rtc.getTime(y, m, d, h, min, s);
    
    // Clear screen (optional line, works on many terminals, tested on Tera Term. Does not take effect in Arduino IDE console unfortunately)
    Serial.println("\033[2J\033[H");

    // Print date and time in plain format
    sprintf(printBuffer, "Date: %04d-%02d-%02d\n", y, m, d);
    Serial.println(printBuffer);
    Serial.println("Time:");

    // Print time in big digits
    printBigTime(h, min, s);

    delay(1000);
}
