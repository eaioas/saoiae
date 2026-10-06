import Foundation

enum SpeedTestService {
    private static let networkQualityPath = "/usr/bin/networkQuality"

    /// Основной способ — встроенная в macOS утилита networkQuality,
    /// запасной — замер через speed.cloudflare.com.
    static func run() async throws -> SpeedResult {
        if FileManager.default.isExecutableFile(atPath: networkQualityPath),
           let result = try? await runNetworkQuality() {
            return result
        }
        return try await runCloudflare()
    }

    // MARK: - networkQuality

    private struct NetworkQualityOutput: Decodable {
        /// бит/с
        let dlThroughput: Double?
        /// бит/с
        let ulThroughput: Double?
        /// мс (есть не во всех версиях macOS)
        let baseRtt: Double?
    }

    private static func runNetworkQuality() async throws -> SpeedResult {
        // -c: вывод в JSON, -s: скачивание и отдача по очереди (точнее, чем параллельно)
        let data = try await runProcess(networkQualityPath, arguments: ["-c", "-s"], timeout: 90)
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let out = try decoder.decode(NetworkQualityOutput.self, from: data)
        guard let dl = out.dlThroughput, let ul = out.ulThroughput else {
            throw AppError.speedTestFailed
        }
        var ping = out.baseRtt
        if ping == nil {
            let session = HTTP.makeSession()
            defer { session.finishTasksAndInvalidate() }
            ping = try? await measureLatency(session)
        }
        return SpeedResult(downloadMbps: dl / 1_000_000, uploadMbps: ul / 1_000_000, pingMs: ping)
    }

    private static func runProcess(_ path: String, arguments: [String], timeout: TimeInterval) async throws -> Data {
        try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: path)
                process.arguments = arguments
                let pipe = Pipe()
                process.standardOutput = pipe
                process.standardError = FileHandle.nullDevice

                do {
                    try process.run()
                } catch {
                    continuation.resume(throwing: error)
                    return
                }

                let killer = DispatchWorkItem {
                    if process.isRunning { process.terminate() }
                }
                DispatchQueue.global().asyncAfter(deadline: .now() + timeout, execute: killer)

                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                process.waitUntilExit()
                killer.cancel()

                if process.terminationStatus == 0 {
                    continuation.resume(returning: data)
                } else {
                    continuation.resume(throwing: AppError.speedTestFailed)
                }
            }
        }
    }

    // MARK: - Cloudflare

    private static let cloudflareBase = "https://speed.cloudflare.com"

    private static func runCloudflare() async throws -> SpeedResult {
        let session = HTTP.makeSession()
        defer { session.finishTasksAndInvalidate() }

        let ping = try? await measureLatency(session)
        let download = try await measureDownload(session)
        let upload = try await measureUpload(session)
        return SpeedResult(downloadMbps: download, uploadMbps: upload, pingMs: ping)
    }

    /// Минимальное время запроса из нескольких попыток, в мс.
    private static func measureLatency(_ session: URLSession) async throws -> Double {
        let url = URL(string: "\(cloudflareBase)/__down?bytes=0")!
        var samples: [Double] = []
        for _ in 0..<6 {
            let start = DispatchTime.now()
            _ = try await session.data(for: URLRequest(url: url, timeoutInterval: 5))
            samples.append(elapsedSeconds(since: start) * 1000)
        }
        // Первая попытка включает DNS и TLS-рукопожатие.
        samples.removeFirst()
        guard let best = samples.min() else { throw AppError.speedTestFailed }
        return best
    }

    /// Мбит/с
    private static func measureDownload(_ session: URLSession) async throws -> Double {
        let bytes = 25_000_000
        let url = URL(string: "\(cloudflareBase)/__down?bytes=\(bytes)")!
        let start = DispatchTime.now()
        let (data, _) = try await session.data(for: URLRequest(url: url, timeoutInterval: 60))
        return mbps(bytes: data.count, seconds: elapsedSeconds(since: start))
    }

    /// Мбит/с
    private static func measureUpload(_ session: URLSession) async throws -> Double {
        let payload = Data(count: 10_000_000)
        var request = URLRequest(url: URL(string: "\(cloudflareBase)/__up")!, timeoutInterval: 60)
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        let start = DispatchTime.now()
        _ = try await session.upload(for: request, from: payload)
        return mbps(bytes: payload.count, seconds: elapsedSeconds(since: start))
    }

    private static func elapsedSeconds(since start: DispatchTime) -> Double {
        Double(DispatchTime.now().uptimeNanoseconds - start.uptimeNanoseconds) / 1_000_000_000
    }

    private static func mbps(bytes: Int, seconds: Double) -> Double {
        guard seconds > 0 else { return 0 }
        return Double(bytes) * 8 / seconds / 1_000_000
    }
}
