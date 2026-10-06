// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "IPInfo",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "IPInfo",
            path: "Sources/IPInfo"
        )
    ]
)
