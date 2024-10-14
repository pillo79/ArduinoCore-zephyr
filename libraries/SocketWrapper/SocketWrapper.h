#include <zephyr/net/socket.h>

class ZephyrSocketWrapper {
protected:
    int sock_fd;

public:
    ZephyrSocketWrapper() : sock_fd(-1) {}

    ~ZephyrSocketWrapper() {
        if (sock_fd != -1) {
            ::close(sock_fd);
        }
    }

    bool connect(const char* host, uint16_t port) {
        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        inet_pton(AF_INET, host, &addr.sin_addr);

        sock_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock_fd < 0) {
            return false;
        }

        if (::connect(sock_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
            ::close(sock_fd);
            sock_fd = -1;
            return false;
        }

        return true;
    }

    int available() {
        int count = 0;
        zsock_ioctl(sock_fd, ZFD_IOCTL_FIONREAD, &count);
        return count;
    }

    int recv(uint8_t* buffer, size_t size) {
        if (sock_fd == -1) {
            return -1;
        }
        return ::recv(sock_fd, buffer, size, MSG_DONTWAIT);
    }

    int send(const uint8_t* buffer, size_t size) {
        if (sock_fd == -1) {
            return -1;
        }
        return ::send(sock_fd, buffer, size, 0);
    }

    void close() {
        if (sock_fd != -1) {
            ::close(sock_fd);
            sock_fd = -1;
        }
    }

    friend class ZephyrClient;
};