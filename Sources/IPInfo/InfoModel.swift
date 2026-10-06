import Foundation

@MainActor
final class InfoModel: ObservableObject {
    @Published private(set) var geo: GeoInfo?
    @Published private(set) var geoError: String?
    @Published private(set) var speed: SpeedResult?
    @Published private(set) var speedError: String?
    @Published private(set) var isLoadingGeo = false
    @Published private(set) var isTestingSpeed = false
    @Published private(set) var lastUpdated: Date?

    var isBusy: Bool { isLoadingGeo || isTestingSpeed }

    /// Данные обновляются только по кнопке.
    func refresh() {
        guard !isBusy else { return }
        Task { await performRefresh() }
    }

    private func performRefresh() async {
        isLoadingGeo = true
        isTestingSpeed = true
        geoError = nil
        speedError = nil

        // Сначала IP и местоположение — это быстро и не мешает замеру скорости.
        do {
            geo = try await GeoService.fetch()
        } catch {
            geo = nil
            geoError = error.localizedDescription
        }
        isLoadingGeo = false

        do {
            speed = try await SpeedTestService.run()
        } catch {
            speed = nil
            speedError = error.localizedDescription
        }
        isTestingSpeed = false

        lastUpdated = Date()
    }
}
