#pragma once
#include "FileSystem.h"
#include <sys/stat.h>
#include <cerrno>
#ifdef _WIN32
#include <windows.h>
#endif
namespace fs=std::filesystem;
filesystem::DependencyStatus legacy_dependency_status(const fs::path& path) {
    filesystem::DependencyStatus result;
#ifdef _WIN32
    // Omit OPEN_REPARSE_POINT: observe the target, not the symlink/junction leaf.
    // BACKUP_SEMANTICS also permits directory dependencies. Sharing mirrors stat.
    HANDLE handle = CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr,
        OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, nullptr);
    if (handle == INVALID_HANDLE_VALUE) {
        result.error = std::error_code(static_cast<int>(GetLastError()), std::system_category());
        return result;
    }
    FILE_BASIC_INFO info{};
    const bool ok = GetFileInformationByHandleEx(handle, FileBasicInfo, &info, sizeof(info)) != 0;
    const DWORD error = ok ? ERROR_SUCCESS : GetLastError();
    CloseHandle(handle);
    if (!ok) {
        result.error = std::error_code(static_cast<int>(error), std::system_category());
        return result;
    }
    const auto ticks = static_cast<std::uint64_t>(info.LastWriteTime.QuadPart);
    result.mtime.seconds = static_cast<std::int64_t>(ticks / 10000000ull) - 11644473600ll;
    result.mtime.nanoseconds = static_cast<std::uint32_t>((ticks % 10000000ull) * 100ull);
#else
    struct stat info{};
    if (::stat(path.c_str(), &info) != 0) {
        result.error = std::error_code(errno, std::generic_category());
        return result;
    }
#ifdef __APPLE__
    result.mtime.seconds = info.st_mtimespec.tv_sec;
    result.mtime.nanoseconds = static_cast<std::uint32_t>(info.st_mtimespec.tv_nsec);
#else
    result.mtime.seconds = info.st_mtim.tv_sec;
    result.mtime.nanoseconds = static_cast<std::uint32_t>(info.st_mtim.tv_nsec);
#endif
#endif
    result.exists = true;
    return result;
}
