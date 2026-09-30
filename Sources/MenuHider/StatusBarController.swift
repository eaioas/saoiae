import AppKit

/// Управляет двумя элементами в menu bar:
/// - шеврон `⌄` — иконка программы, клик сворачивает/разворачивает скрытые иконки;
/// - разделитель `│` — всё, что левее него, считается скрытым.
///
/// Скрытие работает так: в свёрнутом состоянии разделитель растягивается
/// на огромную ширину и выталкивает иконки слева от себя за край экрана.
@MainActor
final class StatusBarController: NSObject {
    private enum Layout {
        static let collapsedSeparatorLength: CGFloat = 10_000
    }

    private enum AutosaveName {
        static let chevron = "MenuHider.chevron"
        static let separator = "MenuHider.separator"
    }

    private enum DefaultsKey {
        static let didShowWelcome = "didShowWelcome"
    }

    private let chevronItem: NSStatusItem
    private let separatorItem: NSStatusItem
    private(set) var isCollapsed = false

    override init() {
        Self.seedInitialPositions()

        // Элементы, созданные позже, встают левее — поэтому сначала шеврон, потом разделитель.
        chevronItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        chevronItem.autosaveName = AutosaveName.chevron
        separatorItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        separatorItem.autosaveName = AutosaveName.separator

        super.init()

        configureButton(chevronItem.button, toolTip: "MenuHider: клик — показать/скрыть, правый клик — меню")
        configureButton(separatorItem.button, toolTip: "Иконки левее этой черты скрываются")
        setCollapsed(false, userInitiated: false)

        // Позиции элементов становятся известны только после первой раскладки menu bar.
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            self.setCollapsed(true, userInitiated: false)
            self.showWelcomeIfNeeded()
        }
    }

    // MARK: - Сворачивание

    func toggle() {
        setCollapsed(!isCollapsed, userInitiated: true)
    }

    private func setCollapsed(_ collapsed: Bool, userInitiated: Bool) {
        var collapsed = collapsed
        if collapsed && !isSeparatorLeftOfChevron {
            // Иначе шеврон уедет за экран вместе со скрытыми иконками и вернуть его будет нечем.
            collapsed = false
            if userInitiated {
                showAlert(
                    title: "Разделитель стоит не на месте",
                    text: "Черта │ должна находиться левее значка ⌄. Зажмите ⌘ и перетащите её левее, затем попробуйте снова."
                )
            }
        }

        isCollapsed = collapsed
        separatorItem.length = collapsed ? Layout.collapsedSeparatorLength : NSStatusItem.variableLength
        separatorItem.button?.image = collapsed ? nil : Self.dividerImage
        chevronItem.button?.image = Self.chevronImage(pointingUp: !collapsed)
    }

    /// Разделитель обязан стоять левее шеврона.
    private var isSeparatorLeftOfChevron: Bool {
        guard let separatorFrame = separatorItem.button?.window?.frame,
              let chevronFrame = chevronItem.button?.window?.frame
        else { return true }
        return separatorFrame.maxX <= chevronFrame.minX + 1
    }

    // MARK: - Клики и меню

    private func configureButton(_ button: NSStatusBarButton?, toolTip: String) {
        guard let button else { return }
        button.target = self
        button.action = #selector(statusItemClicked(_:))
        button.sendAction(on: [.leftMouseUp, .rightMouseUp])
        button.toolTip = toolTip
    }

    @objc private func statusItemClicked(_ sender: NSStatusBarButton) {
        let event = NSApp.currentEvent
        let isContextClick = event?.type == .rightMouseUp || event?.modifierFlags.contains(.control) == true
        if isContextClick {
            showContextMenu()
        } else {
            toggle()
        }
    }

    private func showContextMenu() {
        let menu = NSMenu()

        let toggleItem = NSMenuItem(
            title: isCollapsed ? "Показать скрытые иконки" : "Скрыть иконки",
            action: #selector(toggleFromMenu(_:)),
            keyEquivalent: ""
        )
        toggleItem.target = self
        menu.addItem(toggleItem)

        menu.addItem(.separator())

        let launchItem = NSMenuItem(
            title: "Запускать при входе в систему",
            action: #selector(toggleLaunchAtLogin(_:)),
            keyEquivalent: ""
        )
        launchItem.target = self
        launchItem.state = LaunchAtLogin.isEnabled ? .on : .off
        menu.addItem(launchItem)

        let helpItem = NSMenuItem(title: "Как скрыть иконку…", action: #selector(showHelp(_:)), keyEquivalent: "")
        helpItem.target = self
        menu.addItem(helpItem)

        menu.addItem(.separator())

        let quitItem = NSMenuItem(title: "Выйти из MenuHider", action: #selector(quit(_:)), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        // Стандартный приём: временно назначаем меню и «кликаем» по кнопке,
        // чтобы меню открылось ровно под значком. performClick блокирует, пока меню открыто.
        chevronItem.menu = menu
        chevronItem.button?.performClick(nil)
        chevronItem.menu = nil
    }

    @objc private func toggleFromMenu(_ sender: NSMenuItem) {
        toggle()
    }

    @objc private func toggleLaunchAtLogin(_ sender: NSMenuItem) {
        LaunchAtLogin.setEnabled(!LaunchAtLogin.isEnabled)
    }

    @objc private func showHelp(_ sender: NSMenuItem) {
        showHowToHide()
    }

    @objc private func quit(_ sender: NSMenuItem) {
        NSApp.terminate(nil)
    }

    // MARK: - Подсказки

    private func showWelcomeIfNeeded() {
        let defaults = UserDefaults.standard
        guard !defaults.bool(forKey: DefaultsKey.didShowWelcome) else { return }
        defaults.set(true, forKey: DefaultsKey.didShowWelcome)
        showHowToHide()
    }

    private func showHowToHide() {
        showAlert(
            title: "Как скрыть иконку",
            text: """
            1. Нажмите ⌄ в menu bar — появится черта │.
            2. Зажмите ⌘ и перетащите ненужную иконку левее черты.
            3. Нажмите ⌄ ещё раз — всё, что левее │, скроется.

            Правый клик по ⌄ открывает меню.
            """
        )
    }

    private func showAlert(title: String, text: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = text
        alert.addButton(withTitle: "Понятно")
        NSApp.activate(ignoringOtherApps: true)
        alert.runModal()
    }

    // MARK: - Картинки и начальные позиции

    private static func chevronImage(pointingUp: Bool) -> NSImage? {
        let config = NSImage.SymbolConfiguration(pointSize: 13, weight: .semibold)
        let image = NSImage(
            systemSymbolName: pointingUp ? "chevron.up" : "chevron.down",
            accessibilityDescription: pointingUp ? "Скрыть иконки" : "Показать скрытые иконки"
        )?.withSymbolConfiguration(config)
        image?.isTemplate = true
        return image
    }

    private static let dividerImage: NSImage = {
        let image = NSImage(size: NSSize(width: 9, height: 16), flipped: false) { rect in
            NSColor.black.setFill()
            NSBezierPath(
                roundedRect: NSRect(x: rect.midX - 0.75, y: 1, width: 1.5, height: rect.height - 2),
                xRadius: 0.75,
                yRadius: 0.75
            ).fill()
            return true
        }
        image.isTemplate = true
        return image
    }()

    /// При самом первом запуске ставим шеврон крайним справа, а разделитель — сразу левее него.
    /// Дальше macOS сама запоминает позиции, которые выберет пользователь.
    private static func seedInitialPositions() {
        let defaults = UserDefaults.standard
        let seeds: [(name: String, position: Double)] = [
            (AutosaveName.chevron, 0),
            (AutosaveName.separator, 1),
        ]
        for seed in seeds {
            let key = "NSStatusItem Preferred Position \(seed.name)"
            if defaults.object(forKey: key) == nil {
                defaults.set(seed.position, forKey: key)
            }
        }
    }
}
