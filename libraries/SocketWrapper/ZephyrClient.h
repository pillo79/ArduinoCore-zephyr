#include "SocketWrapper.h"
#include "api/Client.h"
#include "zephyr/sys/printk.h"

class ZephyrClient : public arduino::Client, ZephyrSocketWrapper {
public:
    int connect(const char* host, uint16_t port) override {
        return ZephyrSocketWrapper::connect(host, port);
    }
    int connect(IPAddress ip, uint16_t port) {
        return 0;
    }
    uint8_t connected() override {
        return sock_fd != -1;
    }
    int available() override {
        return ZephyrSocketWrapper::available();
    }
    int read() override {
        uint8_t c;
        read(&c, 1);
        return c;
    }
    int read(uint8_t* buffer, size_t size) override {
        auto received = recv(buffer, size);

        if (received == 0) {
			return 0;
		} else if (received < 0) {
			if (errno == EAGAIN || errno == EWOULDBLOCK) {
				return 0;
			} else {
				return 0;
			}
		}
        return received;
    }
    size_t write(uint8_t c) override {
        return write(&c, 1);
    }
    size_t write(const uint8_t* buffer, size_t size) override {
        return send(buffer, size);
    }
    void flush() override {
        // No-op
    }
    int peek() override {
        // No-op
    }
    void stop() override {
        // No-op
    }
    operator bool() {
        return sock_fd != -1;
    }
};