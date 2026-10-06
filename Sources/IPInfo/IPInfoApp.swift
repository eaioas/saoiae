import SwiftUI

@main
struct IPInfoApp: App {
    @StateObject private var model = InfoModel()
    @StateObject private var launchAtLogin = LaunchAtLogin()

    var body: some Scene {
        MenuBarExtra("IP Info", systemImage: "globe") {
            ContentView()
                .environmentObject(model)
                .environmentObject(launchAtLogin)
        }
        .menuBarExtraStyle(.window)
    }
}
