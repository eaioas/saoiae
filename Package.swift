// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "MenuHider",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "MenuHider",
            path: "Sources/MenuHider"
        )
    ]
)
