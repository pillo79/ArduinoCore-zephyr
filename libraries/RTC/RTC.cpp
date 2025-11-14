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

/**
 * @brief RTC library constructor
 *
 * Constructor used with the STM32 microcontroller based boards (OPTA, PORTENTA H7, GIGA R1)
 *
 */
ArduinoRTC::ArduinoRTC()
{
    rtc_dev = DEVICE_DT_GET(RTC_NODE);
}

/**
 * @brief RTC library classic begin() function
 *
 * Takes care of the underlying STM32 RTC HAL driver initalization
 *
 * @return bool operation result
 */
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

/**
 * @brief RTC library setter function
 *
 * Used to set the time and data with a single function call
 *
 * @param int year to be set
 * @param int month to be set
 * @param int day to be set
 * @param int hour to be set
 * @param int minute to be set
 * @param int second to be set
 * @return int operation result
 */
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

/**
 * @brief RTC library getter
 *
 * Used to set the time and data with a single function call
 *
 * @param int reference to currently set year
 * @param int reference to currently set month
 * @param int reference to currently set day of month
 * @param int reference to currently set hour
 * @param int reference to currently set minute
 * @param int reference to currently set second
 */
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

/**
 * @brief RTC library setter
 *
 * Used to set the alarm time through a single function call
 *
 * @param int year to be set
 * @param int month to be set
 * @param int day to be set
 * @param int hour to be set
 * @param int minute to be set
 * @param int second to be set
 * @return int operation result
 */
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

/**
 * @brief RTC library getter
 *
 * Used to get the time and date of the currently set alarm
 *
 * @param int reference to currently set year
 * @param int reference to currently set month
 * @param int reference to currently set day of month
 * @param int reference to currently set hour
 * @param int reference to currently set minute
 * @param int reference to currently set second
 * @return int operation result
 */
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

/**
 * @brief RTC utility function
 *
 * Used to cancel a previously set alarm
 *
 * @return int operation result
 */
int ArduinoRTC::cancelAlarm()
{
    // Seting time with value zero cancels it
    struct rtc_time dummy = {0};
    return rtc_alarm_set_time(rtc_dev, alarmId, 0, &dummy);
}

/**
 * @brief RTC utility function
 *
 * Used to check if an alarm is currently set
 *
 * @return bool operation result, true for alarm pening, false otherwise
 */
bool ArduinoRTC::isAlarmPending()
{
    int ret = rtc_alarm_is_pending(rtc_dev, alarmId);
    return ret > 0;
}

/**
 * @brief RTC callback function
 *
 * This alarm callback wrapper is needed to make the connection between C-style low level driver function callabacks
 * which need to be static and the objects derived from the RTC class;
 * You do not need to call this direcly in the app
 *
 * @param const struct device *dev is the hardware device (not used at this level)
 * @param uint16_t id is an event/alarm identifier
 * @param void *user_data is a void pointer the user can set when registering the callback
 */
void ArduinoRTC::alarmCallbackWrapper(const struct device *dev, uint16_t id, void *user_data)
{
    ArduinoRTC *self = static_cast<ArduinoRTC *>(user_data);
    if (self && self->userAlarmCallback) {
        self->userAlarmCallback(self->userAlarmCallbackData);
    }
}

/**
 * @brief RTC utility function
 *
 * This function allows for updating the user callback and the message passed to it
 *
 * @param RTCUpdateCallback cb is the new callback which will be called in the app when the event fires later on
 * @param void *user_data is a void pointer the user can set when registering the callback
 */
int ArduinoRTC::setUpdateCallback(RTCUpdateCallback cb, void *user_data)
{
    userUpdateCallback = cb;
    userUpdateCallbackData = user_data;

    return rtc_update_set_callback(rtc_dev, ArduinoRTC::updateCallbackWrapper, this);
}

/**
 * @brief RTC utility function
 *
 * This function is a wrapper which allows for connecting the low level driver and the registered callback with the instance of the object we use in the application sketch
 *
 * @param const struct device *dev is the hardware device (not used at this level)
 * @param void *user_data is a void pointer the user can set when registering the callback
 */
void ArduinoRTC::updateCallbackWrapper(const struct device *dev, void *user_data)
{
    ArduinoRTC *self = static_cast<ArduinoRTC *>(user_data);
    if (self && self->userUpdateCallback) {
        self->userUpdateCallback(self->userUpdateCallbackData);
    }
}

/**
 * @brief Sets the RTC calibration value.
 *
 * This function writes a calibration value to the RTC hardware to adjust
 * timing accuracy. A positive or negative calibration factor may be applied,
 * depending on whether the clock is running fast or slow.
 *
 * @param calibration The calibration adjustment value in parts per million (ppm).
 * @return 0 if successful, or a negative error code on failure.
 */
int ArduinoRTC::setCalibration(int32_t calibration)
{
    return rtc_set_calibration(rtc_dev, calibration);
}


/**
 * @brief Retrieves the current RTC calibration value.
 *
 * This function reads the current calibration adjustment applied to the RTC.
 *
 * @param calibration Reference to an integer where the current calibration
 *        value (in parts per million) will be stored.
 * @return 0 if successful, or a negative error code on failure.
 */
int ArduinoRTC::getCalibration(int32_t &calibration)
{
    return rtc_get_calibration(rtc_dev, &calibration);
}

#elif defined(ARDUINO_NANO33BLE) || defined(ARDUINO_NICLA_SENSE_ME)

#define COUNTER_NODE DT_NODELABEL(rtc2)
LOG_MODULE_REGISTER(ArduinoRTC);

/**
 * @brief Static alarm handler for the RTC driver.
 *
 * This function acts as a static wrapper between the hardware interrupt and
 * the user-defined callback. It retrieves the relevant `ArduinoRTC` instance
 * from the provided `user_data` and invokes the user’s callback function.
 *
 * @param dev Pointer to the RTC device structure (hardware driver).
 * @param chan_id The alarm channel identifier.
 * @param ticks The current tick count at the time of the alarm.
 * @param user_data Pointer to user-defined data (the ArduinoRTC instance).
 */
void ArduinoRTC::alarmHandler(const struct device *dev, uint8_t chan_id, uint32_t ticks, void *user_data)
{
    ArduinoRTC *rtc = static_cast<ArduinoRTC *>(user_data);
    if (rtc->user_callback) {
        rtc->user_callback(dev, chan_id, ticks, rtc->user_data);
    }
}

/**
 * @brief Constructs an ArduinoRTC object.
 *
 * Initializes internal variables, sets default offsets, and retrieves
 * the hardware RTC counter device.
 */
ArduinoRTC::ArduinoRTC()
{
    counter_dev = DEVICE_DT_GET(COUNTER_NODE);
    timeOffset = 0;
    user_callback = nullptr;
    user_data = nullptr;
}

/**
 * @brief Initializes the RTC hardware interface.
 *
 * This function checks if the RTC device is ready and starts the counter.
 *
 * @return true if the device is ready and successfully started, false otherwise.
 */
bool ArduinoRTC::begin()
{
    if (!device_is_ready(counter_dev)) {
        return false;
    }

    counter_start(counter_dev);
    return true;
}

/**
 * @brief Sets the current RTC time.
 *
 * This function converts a date and time into epoch format and adjusts the
 * internal time offset based on the current tick counter.
 *
 * @param year   The current year (e.g., 2025).
 * @param month  The current month (1–12).
 * @param day    The day of the month (1–31).
 * @param hour   The hour (0–23).
 * @param minute The minute (0–59).
 * @param second The second (0–59).
 * @return 0 if successful, or a negative error code if frequency or ticks are invalid.
 */
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

/**
 * @brief Retrieves the current RTC time.
 *
 * This function reads the current counter value, applies the time offset,
 * and converts the epoch time to a human-readable date and time.
 *
 * @param year   Reference to store the current year.
 * @param month  Reference to store the current month.
 * @param day    Reference to store the current day.
 * @param hour   Reference to store the current hour.
 * @param minute Reference to store the current minute.
 * @param second Reference to store the current second.
 * @return 0 if successful.
 */
int ArduinoRTC::getTime(int &year, int &month, int &day, int &hour, int &minute, int &second)
{
    uint32_t ticks;
    counter_get_value(counter_dev, &ticks);

    uint32_t freq = counter_get_frequency(counter_dev);
    time_t now = timeOffset + (ticks / freq);

    epochToDatetime(now, year, month, day, hour, minute, second);
    return 0;
}

/**
 * @brief Sets an RTC alarm.
 *
 * This function schedules an alarm for a specific date and time. When the
 * target time is reached, the registered user callback is invoked.
 *
 * @param year      Target alarm year.
 * @param month     Target alarm month.
 * @param day       Target alarm day.
 * @param hour      Target alarm hour.
 * @param minute    Target alarm minute.
 * @param second    Target alarm second.
 * @param callback  Function pointer to the user-defined callback.
 * @param cb_user_data Pointer to user data passed to the callback when triggered.
 * @return 0 if successful, or a negative error code if the target time is invalid.
 */
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

/**
 * @brief Cancels the currently scheduled alarm.
 *
 * This function stops any active alarm and clears the registered callback
 * and user data.
 */
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

/**
 * @brief Converts a date and time to Unix epoch seconds.
 *
 * This utility function calculates the number of seconds since
 * January 1, 1970 (the Unix epoch) for the provided date and time.
 *
 * @param year   Year value (e.g., 2025).
 * @param month  Month value (1–12).
 * @param day    Day value (1–31).
 * @param hour   Hour value (0–23).
 * @param minute Minute value (0–59).
 * @param second Second value (0–59).
 * @return Corresponding epoch time in seconds.
 */
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

/**
 * @brief Converts Unix epoch seconds to a date and time.
 *
 * This utility function breaks down a given epoch timestamp into a
 * human-readable calendar date and time.
 *
 * @param t       Epoch time in seconds.
 * @param year    Reference to store the year.
 * @param month   Reference to store the month.
 * @param day     Reference to store the day.
 * @param hour    Reference to store the hour.
 * @param minute  Reference to store the minute.
 * @param second  Reference to store the second.
 */
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
