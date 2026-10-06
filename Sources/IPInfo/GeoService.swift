import Foundation

enum GeoService {
    /// Основной источник — ipwho.is, запасной — ipapi.co.
    static func fetch() async throws -> GeoInfo {
        do {
            return try await fetchFromIPWhoIs()
        } catch {
            return try await fetchFromIPAPI()
        }
    }

    // MARK: - ipwho.is

    private struct IPWhoIsResponse: Decodable {
        struct Connection: Decodable {
            let isp: String?
            let org: String?
        }

        let success: Bool?
        let message: String?
        let ip: String?
        let country: String?
        let countryCode: String?
        let city: String?
        let connection: Connection?
    }

    private static func fetchFromIPWhoIs() async throws -> GeoInfo {
        let url = URL(string: "https://ipwho.is/?lang=ru")!
        let r = try await HTTP.getJSON(IPWhoIsResponse.self, from: url)
        guard r.success != false, let ip = r.ip else {
            throw AppError.geoFailed(r.message ?? "ipwho.is")
        }
        return makeInfo(
            ip: ip,
            countryCode: r.countryCode,
            country: r.country,
            city: r.city,
            provider: r.connection?.isp ?? r.connection?.org
        )
    }

    // MARK: - ipapi.co

    private struct IPAPIResponse: Decodable {
        let error: Bool?
        let reason: String?
        let ip: String?
        let city: String?
        let countryName: String?
        let countryCode: String?
        let org: String?
    }

    private static func fetchFromIPAPI() async throws -> GeoInfo {
        let url = URL(string: "https://ipapi.co/json/")!
        let r = try await HTTP.getJSON(IPAPIResponse.self, from: url)
        guard r.error != true, let ip = r.ip else {
            throw AppError.geoFailed(r.reason ?? "ipapi.co")
        }
        return makeInfo(
            ip: ip,
            countryCode: r.countryCode,
            country: r.countryName,
            city: r.city,
            provider: r.org
        )
    }

    // MARK: - Helpers

    private static func makeInfo(
        ip: String,
        countryCode: String?,
        country: String?,
        city: String?,
        provider: String?
    ) -> GeoInfo {
        let code = countryCode ?? ""
        // Название страны берём из системной локализации — так оно всегда по-русски.
        let localizedCountry = code.isEmpty
            ? nil
            : Locale(identifier: "ru_RU").localizedString(forRegionCode: code)
        return GeoInfo(
            ip: ip,
            countryCode: code,
            country: localizedCountry ?? country ?? "Неизвестно",
            city: nonEmpty(city) ?? "—",
            provider: nonEmpty(provider) ?? "—"
        )
    }

    private static func nonEmpty(_ s: String?) -> String? {
        guard let s, !s.trimmingCharacters(in: .whitespaces).isEmpty else { return nil }
        return s
    }
}
