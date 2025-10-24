#include "RTC.h"
#include <zephyr/devicetree.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/counter.h>
#include <stdio.h>

ArduinoRTC::~ArduinoRTC(){}

bool ArduinoRTC::setYear(int year)
{
    bool status = false;
    int currentYear, month, day, hour, minute, second;
    int retVal = getTime(currentYear, month, day, hour, minute, second);
    if(retVal == 0)
    {
        retVal = setTime(year, month, day, hour, minute, second);
        if(retVal == 0u)
        {
            status = true;
        }
    }
}

bool ArduinoRTC::setMonthOfYear(int month)
{
    bool status = false;
    int year, currentMonth, day, hour, minute, second;
    int retVal = getTime(year, currentMonth, day, hour, minute, second);
    if(retVal == 0)
    {
        retVal = setTime(year, month, day, hour, minute, second);
        if(retVal == 0u)
        {
            status = true;
        }
    }
}

bool ArduinoRTC::setDayOfMonth(int day)
{
    bool status = false;
    int year, month, currentDay, hour, minute, second;
    int retVal = getTime(year, month, currentDay, hour, minute, second);
    if(retVal == 0)
    {
        retVal = setTime(year, month, day, hour, minute, second);
        if(retVal == 0u)
        {
            status = true;
        }
    }
}

bool ArduinoRTC::setHour(int hour)
{
    bool status = false;
    int year, month, day, currentHour, minute, second;
    int retVal = getTime(year, month, day, currentHour, minute, second);
    if(retVal == 0)
    {
        retVal = setTime(year, month, day, hour, minute, second);
        if(retVal == 0u)
        {
            status = true;
        }
    }
}

bool ArduinoRTC::setMinute(int minute)
{
    bool status = false;
    int year, month, day, hour, currentMinute, second;
    int retVal = getTime(year, month, day, hour, currentMinute, second);
    if(retVal == 0)
    {
        retVal = setTime(year, month, day, hour, minute, second);
        if(retVal == 0u)
        {
            status = true;
        }
    }
}

bool ArduinoRTC::setSecond(int second)
{
    bool status = false;
    int year, month, day, hour, minute, currentSecond;
    int retVal = getTime(year, month, day, hour, minute, currentSecond);
    if(retVal == 0)
    {
        retVal = setTime(year, month, day, hour, minute, second);
        if(retVal == 0u)
        {
            status = true;
        }
    }
}

int ArduinoRTC::getYear()
{
    int year, month, day, hour, minute, second;
    int retVal = getTime(year, month, day, hour, minute, second);
    if(retVal == 0)
    {
        return year;
    }
}

int ArduinoRTC::getMonth()
{
    int year, month, day, hour, minute, second;
    int retVal = getTime(year, month, day, hour, minute, second);
    if(retVal == 0)
    {
        return month;
    }
}

int ArduinoRTC::getDayOfMonth()
{
    int year, month, day, hour, minute, second;
    int retVal = getTime(year, month, day, hour, minute, second);
    if(retVal == 0)
    {
        return day;
    }
}

int ArduinoRTC::getHour()
{
    int year, month, day, hour, minute, second;
    int retVal = getTime(year, month, day, hour, minute, second);
    if(retVal == 0)
    {
        return hour;
    }
}

int ArduinoRTC::getMinutes()
{
    int year, month, day, hour, minute, second;
    int retVal = getTime(year, month, day, hour, minute, second);
    if(retVal == 0)
    {
        return minute;
    }
}

int ArduinoRTC::getSeconds()
{
    int year, month, day, hour, minute, second;
    int retVal = getTime(year, month, day, hour, minute, second);
    if(retVal == 0)
    {
        return second;
    }
}

#if defined(ARDUINO_GIGA) || defined(ARDUINO_PORTENTA_H7) || defined(ARDUINO_OPTA)
#define RTC_NODE DT_NODELABEL(rtc)

ArduinoRTC::ArduinoRTC()
{
    rtc_dev = DEVICE_DT_GET(RTC_NODE);
}

bool ArduinoRTC::begin()
{
    if (!device_is_ready(rtc_dev)) {
        printk("RTC:: not ready\n");
        return false;
    }

    // Register the alarm callback (even if not active yet)
    rtc_alarm_set_callback(rtc_dev, alarmId, ArduinoRTC::alarmCallbackWrapper, this);

    return true;
}

int ArduinoRTC::setTime(int year, int month, int day, int hour, int minute, int second)
{
    struct rtc_time time = {
        .tm_sec = second,
        .tm_min = minute,
        .tm_hour = hour,
        .tm_mday = day,
        .tm_mon = month - 1,
        .tm_year = year - 1900,
    };
    return rtc_set_time(rtc_dev, &time);
}

int ArduinoRTC::getTime(int &year, int &month, int &day, int &hour, int &minute, int &second)
{
    struct rtc_time time;
    int ret = rtc_get_time(rtc_dev, &time);
    if (ret < 0) return ret;

    year = time.tm_year + 1900;
    month = time.tm_mon + 1;
    day = time.tm_mday;
    hour = time.tm_hour;
    minute = time.tm_min;
    second = time.tm_sec;

    return 0;
}

// ------------------- ALARM API -------------------------

int ArduinoRTC::setAlarm(int year, int month, int day, int hour, int minute, int second, RTCAlarmCallback cb, void *user_data)
{
    struct rtc_time alarm_time = {
        .tm_sec = second,
        .tm_min = minute,
        .tm_hour = hour,
        .tm_mday = day,
        .tm_mon = month - 1,
        .tm_year = year - 1900,
    };

    uint16_t supported_mask = 0;
    int ret = rtc_alarm_get_supported_fields(rtc_dev, alarmId, &supported_mask);
    if (ret < 0) return ret;

    // Build the actual mask based on what we intend to set
    uint16_t mask = 0;
    if (supported_mask & RTC_ALARM_TIME_MASK_SECOND)    mask |= RTC_ALARM_TIME_MASK_SECOND;
    if (supported_mask & RTC_ALARM_TIME_MASK_MINUTE)    mask |= RTC_ALARM_TIME_MASK_MINUTE;
    if (supported_mask & RTC_ALARM_TIME_MASK_HOUR)      mask |= RTC_ALARM_TIME_MASK_HOUR;
    if (supported_mask & RTC_ALARM_TIME_MASK_MONTHDAY)  mask |= RTC_ALARM_TIME_MASK_MONTHDAY;
    if (supported_mask & RTC_ALARM_TIME_MASK_MONTH)     mask |= RTC_ALARM_TIME_MASK_MONTH;
    if (supported_mask & RTC_ALARM_TIME_MASK_YEAR)      mask |= RTC_ALARM_TIME_MASK_YEAR;

    // Save user callback
    userAlarmCallback = cb;
    userAlarmCallbackData = user_data;

    return rtc_alarm_set_time(rtc_dev, alarmId, mask, &alarm_time);
}

int ArduinoRTC::getAlarm(int &year, int &month, int &day, int &hour, int &minute, int &second)
{
    struct rtc_time alarm_time;
    uint16_t mask = 0;

    int ret = rtc_alarm_get_time(rtc_dev, alarmId, &mask, &alarm_time);
    if (ret < 0) return ret;

    year = alarm_time.tm_year + 1900;
    month = alarm_time.tm_mon + 1;
    day = alarm_time.tm_mday;
    hour = alarm_time.tm_hour;
    minute = alarm_time.tm_min;
    second = alarm_time.tm_sec;

    return 0;
}

int ArduinoRTC::cancelAlarm()
{
    // Seting time with value zero cancels it
    struct rtc_time dummy = {0};
    return rtc_alarm_set_time(rtc_dev, alarmId, 0, &dummy);
}

bool ArduinoRTC::isAlarmPending()
{
    int ret = rtc_alarm_is_pending(rtc_dev, alarmId);
    return ret > 0;
}

// ------------------- CALLBACKS -------------------------

void ArduinoRTC::alarmCallbackWrapper(const struct device *dev, uint16_t id, void *user_data)
{
    ArduinoRTC *self = static_cast<ArduinoRTC *>(user_data);
    if (self && self->userAlarmCallback) {
        self->userAlarmCallback(self->userAlarmCallbackData);
    }
}

int ArduinoRTC::setUpdateCallback(RTCUpdateCallback cb, void *user_data)
{
    userUpdateCallback = cb;
    userUpdateCallbackData = user_data;

    return rtc_update_set_callback(rtc_dev, ArduinoRTC::updateCallbackWrapper, this);
}

void ArduinoRTC::updateCallbackWrapper(const struct device *dev, void *user_data)
{
    ArduinoRTC *self = static_cast<ArduinoRTC *>(user_data);
    if (self && self->userUpdateCallback) {
        self->userUpdateCallback(self->userUpdateCallbackData);
    }
}

// ------------------- CALIBRATION -------------------------

int ArduinoRTC::setCalibration(int32_t calibration)
{
    return rtc_set_calibration(rtc_dev, calibration);
}

int ArduinoRTC::getCalibration(int32_t &calibration)
{
    return rtc_get_calibration(rtc_dev, &calibration);
}

#elif defined(ARDUINO_NANO33BLE) || defined(ARDUINO_NICLA_SENSE_ME)

// ------------------- NRF Boards --------------------------

#define COUNTER_NODE DT_NODELABEL(rtc2)
LOG_MODULE_REGISTER(ArduinoRTC);

// Static callback handler
void ArduinoRTC::alarmHandler(const struct device *dev, uint8_t chan_id, uint32_t ticks, void *user_data)
{
    ArduinoRTC *rtc = static_cast<ArduinoRTC *>(user_data);
    if (rtc->user_callback) {
        rtc->user_callback(dev, chan_id, ticks, rtc->user_data);
    }
}

ArduinoRTC::ArduinoRTC()
{
    counter_dev = DEVICE_DT_GET(COUNTER_NODE);
    timeOffset = 0;
    user_callback = nullptr;
    user_data = nullptr;
}

// Initialize the RTC
bool ArduinoRTC::begin()
{
    if (!device_is_ready(counter_dev)) {
        return false;
    }

    counter_start(counter_dev);
    return true;
}

int ArduinoRTC::setTime(int year, int month, int day, int hour, int minute, int second)
{
    time_t target = datetimeToEpoch(year, month, day, hour, minute, second);

    uint32_t ticks;
    counter_get_value(counter_dev, &ticks);

    uint32_t freq = counter_get_frequency(counter_dev);
    if (freq == 0) {
        return -1;
    }

    timeOffset = target - (ticks / freq);
    return 0;
}

int ArduinoRTC::getTime(int &year, int &month, int &day, int &hour, int &minute, int &second)
{
    uint32_t ticks;
    counter_get_value(counter_dev, &ticks);

    uint32_t freq = counter_get_frequency(counter_dev);
    time_t now = timeOffset + (ticks / freq);

    epochToDatetime(now, year, month, day, hour, minute, second);
    return 0;
}

int ArduinoRTC::setAlarm(int year, int month, int day, int hour, int minute, int second,
                                void (*callback)(const struct device *dev, uint8_t chan_id, uint32_t ticks, void *user_data),
                                void *cb_user_data)
{
    time_t target_epoch = datetimeToEpoch(year, month, day, hour, minute, second);
    uint32_t freq = counter_get_frequency(counter_dev);
    uint32_t current_ticks;

    if (counter_get_value(counter_dev, &current_ticks) != 0) {
        return -1;
    }

    time_t current_epoch = timeOffset + (current_ticks / freq);
    time_t delta_seconds = target_epoch - current_epoch;

    if (delta_seconds <= 0) {
        return -1;
    }

    uint32_t alarm_ticks = current_ticks + delta_seconds * freq;

    // Save user callback
    user_callback = callback;
    user_data = cb_user_data;

    alarm_cfg.flags = 0; // Absolute alarm
    alarm_cfg.ticks = alarm_ticks;
    alarm_cfg.callback = ArduinoRTC::alarmHandler;
    alarm_cfg.user_data = this;

    int ret = counter_set_channel_alarm(counter_dev, 0, &alarm_cfg);
    if (ret != 0) {
        return ret;
    }

    return 0;
}

// Cancel alarm
void ArduinoRTC::cancelAlarm()
{
    counter_cancel_channel_alarm(counter_dev, 0);
    user_callback = nullptr;
    user_data = nullptr;
}

// Utility functions
static const int days_in_month[] = {
    31, 28, 31, 30, 31, 30,
    31, 31, 30, 31, 30, 31
};

static bool is_leap(int year) {
    return (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0));
}

time_t ArduinoRTC::datetimeToEpoch(int year, int month, int day, int hour, int minute, int second)
{
    int y = year;
    int m = month;
    time_t days = 0;

    for (int i = 1970; i < y; i++) {
        days += is_leap(i) ? 366 : 365;
    }

    for (int i = 1; i < m; i++) {
        days += days_in_month[i - 1];
        if (i == 2 && is_leap(y)) {
            days += 1;
        }
    }

    days += (day - 1);

    return (((days * 24 + hour) * 60 + minute) * 60 + second);
}

void ArduinoRTC::epochToDatetime(time_t t, int &year, int &month, int &day, int &hour, int &minute, int &second)
{
    time_t seconds_in_day = t % 86400;
    time_t days = t / 86400;

    hour = seconds_in_day / 3600;
    minute = (seconds_in_day % 3600) / 60;
    second = seconds_in_day % 60;

    year = 1970;
    while (true) {
        int days_in_year = is_leap(year) ? 366 : 365;
        if (days >= days_in_year) {
            days -= days_in_year;
            year++;
        } else {
            break;
        }
    }

    int m = 0;
    while (true) {
        int dim = days_in_month[m];
        if (m == 1 && is_leap(year)) {
            dim++;
        }

        if (days >= dim) {
            days -= dim;
            m++;
        } else {
            break;
        }
    }

    month = m + 1;
    day = days + 1;
}
#endif
