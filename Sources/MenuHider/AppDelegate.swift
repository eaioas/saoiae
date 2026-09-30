import AppKit

@main
@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusBarController: StatusBarController?

    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        // Без иконки в Dock и без главного меню — приложение живёт только в menu bar.
        app.setActivationPolicy(.accessory)
        app.run()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        LaunchAtLogin.enableOnFirstLaunch()
        statusBarController = StatusBarController()
    }
}
