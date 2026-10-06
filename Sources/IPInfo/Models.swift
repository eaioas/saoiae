import Foundation

struct GeoInfo: Equatable {
    let ip: String
    let countryCode: String
    let country: String
    let city: String
    let provider: String

    /// Эмодзи-флаг из двухбуквенного кода страны (DE → 🇩🇪).
    var flag: String {
        let letters = countryCode.uppercased().unicodeScalars.filter { (65...90).contains($0.value) }
        let scalars = letters.compactMap { Unicode.Scalar(0x1F1E6 + $0.value - 65) }
        guard scalars.count == 2 else { return "🌐" }
        var view = String.UnicodeScalarView()
        view.append(contentsOf: scalars)
        return String(view)
    }
}

struct SpeedResult: Equatable {
    /// Мбит/с
    let downloadMbps: Double
    /// Мбит/с
    let uploadMbps: Double
    /// Миллисекунды
    let pingMs: Double?
}

enum AppError: LocalizedError {
    case badResponse(Int)
    case geoFailed(String)
    case speedTestFailed

    var errorDescription: String? {
        switch self {
        case .badResponse(let code):
            return "Сервер ответил с ошибкой (\(code))"
        case .geoFailed(let message):
            return "Не удалось определить IP: \(message)"
        case .speedTestFailed:
            return "Не удалось измерить скорость"
        }
    }
}

enum HTTP {
    /// Новая ephemeral-сессия на каждый запрос, чтобы не переиспользовать
    /// соединения, открытые до смены сети или включения VPN.
    static func makeSession() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.requestCachePolicy = .reloadIgnoringLocalAndRemoteCacheData
        config.urlCache = nil
        return URLSession(configuration: config)
    }

    static func getJSON<T: Decodable>(_ type: T.Type, from url: URL) async throws -> T {
        let session = makeSession()
        defer { session.finishTasksAndInvalidate() }

        var request = URLRequest(url: url, timeoutInterval: 10)
        request.setValue("IPInfo-macOS/1.0", forHTTPHeaderField: "User-Agent")
        let (data, response) = try await session.data(for: request)
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw AppError.badResponse(http.statusCode)
        }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(T.self, from: data)
    }
}
