import AppKit
import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var model: InfoModel
    @EnvironmentObject private var launchAtLogin: LaunchAtLogin
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            geoSection
            Divider()
            speedSection
            Divider()
            footer
        }
        .padding(14)
        .frame(width: 300)
        .onAppear { launchAtLogin.refreshStatus() }
    }

    // MARK: - Местоположение

    @ViewBuilder
    private var geoSection: some View {
        if model.isLoadingGeo {
            ProgressRow(text: "Определяем IP и местоположение…")
        } else if let error = model.geoError {
            ErrorRow(text: error)
        } else if let geo = model.geo {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 10) {
                    Text(geo.flag).font(.system(size: 30))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(geo.country).font(.headline)
                        Text(geo.city).foregroundStyle(.secondary)
                    }
                }
                HStack {
                    InfoRow(icon: "network", title: "IP", value: geo.ip)
                    Button {
                        copy(geo.ip)
                    } label: {
                        Image(systemName: copied ? "checkmark" : "doc.on.doc")
                    }
                    .buttonStyle(.borderless)
                    .help("Скопировать IP")
                }
                InfoRow(icon: "building.2", title: "Провайдер", value: geo.provider)
            }
        } else {
            Text("Нажмите \(Image(systemName: "arrow.clockwise")) внизу, чтобы получить данные")
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - Скорость

    @ViewBuilder
    private var speedSection: some View {
        if model.isTestingSpeed {
            ProgressRow(text: model.isLoadingGeo ? "Скорость измерим следом…" : "Измеряем скорость (~30 сек)…")
        } else if let error = model.speedError {
            ErrorRow(text: error)
        } else {
            VStack(alignment: .leading, spacing: 8) {
                InfoRow(icon: "arrow.down.circle", title: "Скачивание", value: format(mbps: model.speed?.downloadMbps))
                InfoRow(icon: "arrow.up.circle", title: "Отдача", value: format(mbps: model.speed?.uploadMbps))
                InfoRow(icon: "timer", title: "Пинг", value: format(ms: model.speed?.pingMs))
            }
        }
    }

    // MARK: - Нижняя панель

    private var footer: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Button {
                    model.refresh()
                } label: {
                    if model.isBusy {
                        ProgressView().controlSize(.small).frame(width: 16, height: 16)
                    } else {
                        Image(systemName: "arrow.clockwise").frame(width: 16, height: 16)
                    }
                }
                .buttonStyle(.borderless)
                .disabled(model.isBusy)
                .help("Обновить")

                Text(statusText)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Spacer()

                Menu {
                    Toggle("Запускать при входе", isOn: Binding(
                        get: { launchAtLogin.isEnabled },
                        set: { launchAtLogin.set($0) }
                    ))
                    Button("Объекты входа…") { launchAtLogin.openLoginItemsSettings() }
                    Divider()
                    Button("Выйти") { NSApp.terminate(nil) }
                } label: {
                    Image(systemName: "gearshape")
                }
                .menuStyle(.borderlessButton)
                .menuIndicator(.hidden)
                .fixedSize()
                .help("Настройки")
            }

            if let message = launchAtLogin.message {
                Text(message)
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var statusText: String {
        if model.isBusy { return "обновляем…" }
        guard let date = model.lastUpdated else { return "нет данных" }
        return "обновлено " + date.formatted(date: .omitted, time: .shortened)
    }

    // MARK: - Helpers

    private func copy(_ text: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
        copied = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { copied = false }
    }

    private func format(mbps: Double?) -> String {
        guard let mbps else { return "—" }
        return String(format: mbps >= 100 ? "%.0f Мбит/с" : "%.1f Мбит/с", mbps)
    }

    private func format(ms: Double?) -> String {
        guard let ms else { return "—" }
        return String(format: "%.0f мс", ms)
    }
}

private struct InfoRow: View {
    let icon: String
    let title: String
    let value: String

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .frame(width: 16)
                .foregroundStyle(.secondary)
            Text(title).foregroundStyle(.secondary)
            Spacer(minLength: 8)
            Text(value)
                .monospacedDigit()
                .lineLimit(1)
                .truncationMode(.middle)
                .textSelection(.enabled)
        }
    }
}

private struct ProgressRow: View {
    let text: String

    var body: some View {
        HStack(spacing: 8) {
            ProgressView().controlSize(.small)
            Text(text).foregroundStyle(.secondary)
        }
    }
}

private struct ErrorRow: View {
    let text: String

    var body: some View {
        Label(text, systemImage: "exclamationmark.triangle")
            .foregroundStyle(.orange)
            .fixedSize(horizontal: false, vertical: true)
    }
}
