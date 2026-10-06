import Foundation
import ServiceManagement

@MainActor
final class LaunchAtLogin: ObservableObject {
    @Published private(set) var isEnabled = false
    @Published private(set) var message: String?

    private static let configuredKey = "didConfigureLaunchAtLogin"

    init() {
        // При первом запуске сразу включаем автозапуск.
        if !UserDefaults.standard.bool(forKey: Self.configuredKey) {
            UserDefaults.standard.set(true, forKey: Self.configuredKey)
            set(true)
        } else {
            refreshStatus()
        }
    }

    func set(_ enabled: Bool) {
        do {
            if enabled {
                try SMAppService.mainApp.register()
            } else {
                try SMAppService.mainApp.unregister()
            }
            message = nil
        } catch {
            message = "Автозапуск: \(error.localizedDescription)"
        }
        refreshStatus()
    }

    /// Пользователь мог поменять настройку в Системных настройках.
    func refreshStatus() {
        let status = SMAppService.mainApp.status
        isEnabled = status == .enabled
        if status == .requiresApproval {
            message = "Разрешите автозапуск: Системные настройки → Основные → Объекты входа"
        } else if status == .enabled {
            message = nil
        }
    }

    func openLoginItemsSettings() {
        SMAppService.openSystemSettingsLoginItems()
    }
}
