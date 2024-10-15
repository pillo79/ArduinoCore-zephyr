#pragma once

#include <zephyr/net/socket.h>

class ZephyrSocketWrapper {
protected:
    int sock_fd;

public:
    ZephyrSocketWrapper() : sock_fd(-1) {}
    ZephyrSocketWrapper(int sock_fd) : sock_fd(sock_fd) {}

    ~ZephyrSocketWrapper() {
        if (sock_fd != -1) {
            ::close(sock_fd);
        }
    }

    bool connect(const char* host, uint16_t port) {

        // Resolve address
        struct addrinfo hints;
	    struct addrinfo *res;

	    hints.ai_family = AF_INET;
	    hints.ai_socktype = SOCK_STREAM;

        int resolve_attempts = 100;
        int ret;

	    while (resolve_attempts--) {
            ret = getaddrinfo(host, String(port).c_str(), &hints, &res);

            if (ret == 0) {
                break;
            }
        }

	    if (ret != 0) {
            return false;
        }

        sock_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock_fd < 0) {
            return false;
        }

        if (::connect(sock_fd, res->ai_addr, res->ai_addrlen) < 0) {
            ::close(sock_fd);
            sock_fd = -1;
            return false;
        }

        return true;
    }

    bool connect(IPAddress host, uint16_t port) {

        const char* _host = host.toString().c_str();

        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        inet_pton(AF_INET, _host, &addr.sin_addr);

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

    int recv(uint8_t* buffer, size_t size, int flags = MSG_DONTWAIT) {
        if (sock_fd == -1) {
            return -1;
        }
        return ::recv(sock_fd, buffer, size, flags);
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

    bool bind(uint16_t port) {
        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        addr.sin_addr.s_addr = INADDR_ANY;

        sock_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock_fd < 0) {
            return false;
        }

        zsock_ioctl(sock_fd, ZFD_IOCTL_FIONBIO);

        if (::bind(sock_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
            ::close(sock_fd);
            sock_fd = -1;
            return false;
        }

        return true;
    }

    bool listen(int backlog = 5) {
        if (sock_fd == -1) {
            return false;
        }

        if (::listen(sock_fd, backlog) < 0) {
            ::close(sock_fd);
            sock_fd = -1;
            return false;
        }

        return true;
    }

    int accept() {
        if (sock_fd == -1) {
            return -1;
        }

        return ::accept(sock_fd, nullptr, nullptr);
    }

    friend class ZephyrClient;
};