import Foundation
import os
import ServiceManagement

/// Автозапуск при входе в систему через `SMAppService` (macOS 13+).
/// Работает только для собранного `.app`, а не для бинарника, запущенного через `swift run`.
enum LaunchAtLogin {
    private static let didConfigureKey = "didConfigureLaunchAtLogin"
    private static let logger = Logger(subsystem: "io.github.eaioas.MenuHider", category: "LaunchAtLogin")

    static var isEnabled: Bool {
        SMAppService.mainApp.status == .enabled
    }

    /// При первом запуске включаем автозапуск; дальше решает пользователь.
    static func enableOnFirstLaunch() {
        let defaults = UserDefaults.standard
        guard !defaults.bool(forKey: didConfigureKey) else { return }
        if setEnabled(true) {
            defaults.set(true, forKey: didConfigureKey)
        }
    }

    @discardableResult
    static func setEnabled(_ enabled: Bool) -> Bool {
        let service = SMAppService.mainApp
        do {
            if enabled {
                if service.status != .enabled {
                    try service.register()
                }
                // Пользователь ранее запретил автозапуск в Системных настройках — отправляем его туда.
                if service.status == .requiresApproval {
                    SMAppService.openSystemSettingsLoginItems()
                }
            } else if service.status == .enabled {
                try service.unregister()
            }
            return true
        } catch {
            logger.error("Не удалось изменить автозапуск: \(error.localizedDescription, privacy: .public)")
            return false
        }
    }
}
