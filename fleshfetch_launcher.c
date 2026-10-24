#include <windows.h>
#include <wchar.h>


static const wchar_t *skip_executable(const wchar_t *command_line) {
    const wchar_t *cursor = command_line;
    while (*cursor == L' ' || *cursor == L'\t') {
        cursor++;
    }
    if (*cursor == L'"') {
        cursor++;
        while (*cursor && *cursor != L'"') {
            cursor++;
        }
        if (*cursor == L'"') {
            cursor++;
        }
    } else {
        while (*cursor && *cursor != L' ' && *cursor != L'\t') {
            cursor++;
        }
    }
    while (*cursor == L' ' || *cursor == L'\t') {
        cursor++;
    }
    return cursor;
}


static int show_launch_error(const wchar_t *message) {
    MessageBoxW(NULL, message, L"Fleshfetch could not start", MB_OK | MB_ICONERROR);
    return 1;
}


int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR command_line, int show) {
    wchar_t launcher_path[32768];
    wchar_t root_dir[32768];
    wchar_t runtime_exe[32768];
    wchar_t child_command[32768];
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    DWORD exit_code = 1;

    (void)instance;
    (void)previous;
    (void)command_line;
    (void)show;

    DWORD path_length = GetModuleFileNameW(NULL, launcher_path, 32768);
    if (path_length == 0 || path_length >= 32768) {
        return show_launch_error(L"The Fleshfetch installation path is too long.");
    }

    wcscpy_s(root_dir, 32768, launcher_path);
    wchar_t *separator = wcsrchr(root_dir, L'\\');
    if (separator == NULL) {
        return show_launch_error(L"Fleshfetch could not locate its installation folder.");
    }
    *separator = L'\0';

    if (swprintf_s(
            runtime_exe,
            32768,
            L"%ls\\runtime\\fleshfetch-runtime.exe",
            root_dir
        ) < 0) {
        return show_launch_error(L"Fleshfetch could not construct its runtime path.");
    }
    if (GetFileAttributesW(runtime_exe) == INVALID_FILE_ATTRIBUTES) {
        return show_launch_error(
            L"runtime\\fleshfetch-runtime.exe is missing.\n\n"
            L"Extract the complete Fleshfetch release before launching it."
        );
    }

    SetEnvironmentVariableW(L"FLESHFETCH_ROOT", root_dir);

    const wchar_t *arguments = skip_executable(GetCommandLineW());
    if (*arguments) {
        if (swprintf_s(child_command, 32768, L"\"%ls\" %ls", runtime_exe, arguments) < 0) {
            return show_launch_error(L"The Fleshfetch command line is too long.");
        }
    } else {
        if (swprintf_s(child_command, 32768, L"\"%ls\"", runtime_exe) < 0) {
            return show_launch_error(L"The Fleshfetch command line is too long.");
        }
    }

    startup.cb = sizeof(startup);
    if (!CreateProcessW(
            runtime_exe,
            child_command,
            NULL,
            NULL,
            FALSE,
            0,
            NULL,
            root_dir,
            &startup,
            &process
        )) {
        return show_launch_error(L"Fleshfetch could not launch its runtime executable.");
    }

    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    GetExitCodeProcess(process.hProcess, &exit_code);
    CloseHandle(process.hProcess);

    if (exit_code != 0) {
        wchar_t error_message[1024];
        swprintf_s(
            error_message,
            1024,
            L"The Fleshfetch runtime exited unexpectedly.\n\n"
            L"Exit code: %ld (0x%08lX)\n\n"
            L"If a startup log was created, it is located at:\n"
            L"%%APPDATA%%\\fleshfetch\\startup.log",
            (LONG)exit_code,
            exit_code
        );
        return show_launch_error(error_message);
    }

    return 0;
}
