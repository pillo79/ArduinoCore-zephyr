// RTC.h
#pragma once

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/counter.h>
#include <zephyr/drivers/rtc.h>
#include <time.h>

// Alarm callback types
typedef void (*RTCAlarmCallback)(void *user_data);
typedef void (*RTCUpdateCallback)(void *user_data);

class ArduinoRTC {
public:
    ArduinoRTC();
    bool begin();
    ~ArduinoRTC();

    /* setters */
    bool setDayOfMonth(int day);
    bool setMonthOfYear(int m);
    bool setYear(int year);
    bool setHour(int hour);
    bool setMinute(int minute);
    bool setSecond(int second);

    /* Getters */
    int getDayOfMonth();
    int getMonth();
    int getYear();
    int getHour();
    int getMinutes();
    int getSeconds();

    int setTime(int year, int month, int day, int hour, int minute, int second);
    int getTime(int &year, int &month, int &day, int &hour, int &minute, int &second);
#if defined(ARDUINO_GIGA) || defined(ARDUINO_PORTENTA_H7) || defined(ARDUINO_OPTA)
    int setAlarm(int year, int month, int day, int hour, int minute, int second,
                 RTCAlarmCallback cb = nullptr, void *user_data = nullptr);
    int cancelAlarm();
#elif defined(ARDUINO_NANO33BLE) || defined(ARDUINO_NICLA_SENSE_ME)
    int setAlarm(int year, int month, int day, int hour, int minute, int second,
                void (*callback)(const struct device *dev, uint8_t chan_id, uint32_t ticks, void *user_data),
                void *cb_user_data);
    void cancelAlarm();
#endif
    
#if defined(ARDUINO_GIGA) || defined(ARDUINO_PORTENTA_H7) || defined(ARDUINO_OPTA)
    // Optional APIs (only if supported)
    int getAlarm(int &year, int &month, int &day, int &hour, int &minute, int &second);
    bool isAlarmPending();
    int setUpdateCallback(RTCUpdateCallback cb, void *user_data);
    int setCalibration(int32_t calibration);
    int getCalibration(int32_t &calibration);
#endif


private:
#if defined(ARDUINO_GIGA) || defined(ARDUINO_PORTENTA_H7) || defined(ARDUINO_OPTA)
    const struct device *rtc_dev;

    static void alarmCallbackWrapper(const struct device *dev, uint16_t id, void *user_data);
    static void updateCallbackWrapper(const struct device *dev, void *user_data);

    RTCAlarmCallback userAlarmCallback = nullptr;
    void *userAlarmCallbackData = nullptr;

    RTCUpdateCallback userUpdateCallback = nullptr;
    void *userUpdateCallbackData = nullptr;

    uint16_t alarmId = 0; // default to alarm ID 0
#elif defined(ARDUINO_NANO33BLE) || defined(ARDUINO_NICLA_SENSE_ME)
    const struct device *counter_dev;
    time_t timeOffset;

    // Alarm members
    struct counter_alarm_cfg alarm_cfg;
    void (*user_callback)(const struct device *dev, uint8_t chan_id, uint32_t ticks, void *user_data);
    void *user_data;

    static void alarmHandler(const struct device *dev, uint8_t chan_id, uint32_t ticks, void *user_data);

    time_t datetimeToEpoch(int year, int month, int day, int hour, int minute, int second);
    void epochToDatetime(time_t t, int &year, int &month, int &day, int &hour, int &minute, int &second);
#endif
};