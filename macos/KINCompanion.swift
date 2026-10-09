import AppKit
import CryptoKit
import Foundation
import ImageIO
import Security
import UniformTypeIdentifiers
import Vision

private let confirmation = "I CONSENT TO LOCAL TRAINING"
private let maxFiles = 100_000
private let maxTotalBytes = 10_000_000_000
private let textExtensions = Set(["md", "txt"])
private let imageExtensions = Set(["jpg", "jpeg", "png", "heic", "tif", "tiff"])
private let supportedExtensions = textExtensions.union(imageExtensions)
private let keyService = "org.80twenty.companion"
private let keyAccount = "native-capability-signing-key-v1"

private enum BrokerError: LocalizedError {
    case message(String)
    var errorDescription: String? {
        switch self { case .message(let value): return value }
    }
}

private func signingKey() throws -> Curve25519.Signing.PrivateKey {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: keyService,
        kSecAttrAccount as String: keyAccount,
        kSecReturnData as String: true,
        kSecMatchLimit as String: kSecMatchLimitOne,
    ]
    var result: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    if status == errSecSuccess, let data = result as? Data {
        return try Curve25519.Signing.PrivateKey(rawRepresentation: data)
    }
    guard status == errSecItemNotFound else {
        throw BrokerError.message("Keychain lookup failed (\(status)).")
    }
    let key = Curve25519.Signing.PrivateKey()
    var insert = query
    insert.removeValue(forKey: kSecReturnData as String)
    insert.removeValue(forKey: kSecMatchLimit as String)
    insert[kSecValueData as String] = key.rawRepresentation
    insert[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
    let addStatus = SecItemAdd(insert as CFDictionary, nil)
    guard addStatus == errSecSuccess else {
        throw BrokerError.message("Keychain creation failed (\(addStatus)).")
    }
    return key
}

private func isoDate(_ date: Date) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return formatter.string(from: date)
}

private func canonicalJSON(_ object: Any) throws -> Data {
    try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes])
}

private func sha256(_ data: Data) -> String {
    SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}

private func privacyFindings(_ text: String, allowPersonalData: Bool) -> [String] {
    var expressions: [(String, String)] = [
        ("private key", "-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        ("cloud access key", "\\b(AKIA|ASIA)[A-Z0-9]{16}\\b"),
        ("secret assignment", "(?i)\\b(api[_-]?key|access[_-]?token|password|passwd|secret)\\s*[:=]\\s*[^\\s]{6,}"),
    ]
    if !allowPersonalData {
        expressions.append(("email address", "(?i)\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b"))
        expressions.append(("phone-number-like text", "(?<!\\w)(\\+?\\d[\\d ()-]{7,}\\d)(?!\\w)"))
    }
    return expressions.compactMap { label, pattern in
        let regex = try? NSRegularExpression(pattern: pattern)
        let range = NSRange(text.startIndex..<text.endIndex, in: text)
        return regex?.firstMatch(in: text, range: range) == nil ? nil : label
    }
}

private func localImageDerivative(_ data: Data) throws -> String {
    guard let source = CGImageSourceCreateWithData(data as CFData, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw BrokerError.message("A selected image could not be decoded.")
    }
    let textRequest = VNRecognizeTextRequest()
    textRequest.recognitionLevel = .accurate
    textRequest.usesLanguageCorrection = true
    let classificationRequest = VNClassifyImageRequest()
    let faceRequest = VNDetectFaceRectanglesRequest()
    try VNImageRequestHandler(cgImage: image).perform([textRequest, classificationRequest, faceRequest])

    let recognised = (textRequest.results ?? []).compactMap { $0.topCandidates(1).first?.string }
        .joined(separator: " ").replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
    let labels = (classificationRequest.results ?? []).filter { $0.confidence >= 0.15 }.prefix(12)
        .map { "\($0.identifier) (\(Int($0.confidence * 100))%)" }
    let faceCount = faceRequest.results?.count ?? 0
    var derivative = "# Local image observations\n\n"
    derivative += "Local on-device image analysis found \(faceCount) face-like region(s). Broad classification labels: "
    derivative += labels.isEmpty ? "no confident labels.\n\n" : labels.joined(separator: ", ") + ".\n\n"
    if recognised.count >= 10 {
        derivative += "# Locally recognised image text\n\n" + String(recognised.prefix(4000)) + "\n"
    }
    return derivative
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private var selectedFiles: [URL] = []
    private var selectedFolders: [URL] = []
    private var outputFolder: URL?
    private let scope = NSSegmentedControl(labels: ["Specific files", "Everything compatible in folders"], trackingMode: .selectOne, target: nil, action: nil)
    private let chooseInputs = NSButton(title: "1. Choose exact files…", target: nil, action: nil)
    private let filesLabel = NSTextField(wrappingLabelWithString: "No files selected.")
    private let outputLabel = NSTextField(wrappingLabelWithString: "No private job folder selected.")
    private let acknowledgement = NSButton(checkboxWithTitle: "I have read the scope, risks and withdrawal limitation.", target: nil, action: nil)
    private let phrase = NSTextField()
    private let status = NSTextField(wrappingLabelWithString: "Nothing has been read or created.")

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        let content = NSStackView()
        content.orientation = .vertical
        content.alignment = .leading
        content.spacing = 14
        content.edgeInsets = NSEdgeInsets(top: 24, left: 28, bottom: 24, right: 28)

        let title = NSTextField(labelWithString: "80Twenty local training consent")
        title.font = .systemFont(ofSize: 26, weight: .bold)
        content.addArrangedSubview(title)
        content.addArrangedSubview(NSTextField(wrappingLabelWithString:
            "This native companion uses the macOS file picker. File content is not opened until you approve. Choose exact files, or explicitly opt into every compatible text file inside folders you select."))

        let scopeTitle = NSTextField(labelWithString: "Training scope")
        scopeTitle.font = .systemFont(ofSize: 13, weight: .semibold)
        content.addArrangedSubview(scopeTitle)
        scope.selectedSegment = 0
        scope.target = self
        scope.action = #selector(scopeChanged)
        content.addArrangedSubview(scope)
        chooseInputs.target = self
        chooseInputs.action = #selector(selectFiles)
        content.addArrangedSubview(chooseInputs)
        content.addArrangedSubview(filesLabel)
        let chooseOutput = NSButton(title: "2. Choose private job folder…", target: self, action: #selector(selectOutput))
        content.addArrangedSubview(chooseOutput)
        content.addArrangedSubview(outputLabel)

        let disclosure = NSTextField(wrappingLabelWithString: """
        What approval does: selected UTF-8 Markdown, text and supported image files are read locally and copied under random numbered names into one private job directory. “Everything compatible” recursively includes .md, .txt, .jpg, .jpeg, .png, .heic, .tif and .tiff files in the folders you choose. Images are analysed locally for OCR text, broad labels and face counts; this trains text knowledge about an image, not visual understanding. Content may include personal data. Obvious passwords, API keys, cloud keys and private keys found in text derivatives are rejected. A high emergency ceiling of 100,000 files or 10 GB prevents accidental disk exhaustion.

        The broker signs a 60-minute capability using a key stored in your Keychain. The trainer receives only those snapshots and may run with home-folder and network access denied.

        Public evidence may contain counts, hashes and aggregate metrics only. It may not contain source text, original names, paths, derived examples or model weights. This proof pays no real money.

        Risks: training can memorise source material. Withdrawal stops future jobs and allows local deletion, but cannot reliably remove knowledge from a model already trained. This is experimental and cannot protect a compromised operating system.
        """)
        disclosure.drawsBackground = true
        disclosure.backgroundColor = NSColor.controlBackgroundColor
        disclosure.maximumNumberOfLines = 0
        content.addArrangedSubview(disclosure)
        content.addArrangedSubview(acknowledgement)

        let phraseLabel = NSTextField(labelWithString: "Type exactly: \(confirmation)")
        phraseLabel.font = .systemFont(ofSize: 13, weight: .semibold)
        content.addArrangedSubview(phraseLabel)
        phrase.placeholderString = confirmation
        phrase.widthAnchor.constraint(equalToConstant: 520).isActive = true
        content.addArrangedSubview(phrase)

        let buttons = NSStackView()
        buttons.orientation = .horizontal
        buttons.spacing = 12
        let approve = NSButton(title: "Approve and create capability", target: self, action: #selector(approve))
        approve.keyEquivalent = "\r"
        let decline = NSButton(title: "Decline", target: self, action: #selector(decline))
        buttons.addArrangedSubview(approve)
        buttons.addArrangedSubview(decline)
        content.addArrangedSubview(buttons)
        status.textColor = .secondaryLabelColor
        content.addArrangedSubview(status)

        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true
        scroll.documentView = content
        content.translatesAutoresizingMaskIntoConstraints = false
        content.widthAnchor.constraint(equalTo: scroll.contentView.widthAnchor).isActive = true

        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 780, height: 760),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "80Twenty Companion"
        window.contentView = scroll
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    @objc private func scopeChanged() {
        selectedFiles = []
        selectedFolders = []
        filesLabel.stringValue = "No files or folders selected."
        if scope.selectedSegment == 0 {
            chooseInputs.title = "1. Choose exact files…"
            status.stringValue = "Specific-file mode. Personal identifiers are rejected."
        } else {
            chooseInputs.title = "1. Choose folders for everything…"
            status.stringValue = "Everything-compatible mode may include personal data. No content is read before approval."
        }
    }

    @objc private func selectFiles() {
        let panel = NSOpenPanel()
        let folderMode = scope.selectedSegment == 1
        panel.title = folderMode ? "Choose folders for everything-compatible training" : "Choose exact files for this 80Twenty job"
        panel.message = "Content will not be opened until you approve in the next step."
        panel.canChooseFiles = !folderMode
        panel.canChooseDirectories = folderMode
        panel.allowsMultipleSelection = true
        if !folderMode {
            panel.allowedContentTypes = supportedExtensions.sorted().compactMap { UTType(filenameExtension: $0) }
        }
        guard panel.runModal() == .OK else { return }
        if folderMode {
            selectedFolders = Array(panel.urls.prefix(8))
            selectedFiles = []
            filesLabel.stringValue = selectedFolders.enumerated().map { "\($0.offset + 1). \($0.element.lastPathComponent)/ (recursive)" }.joined(separator: "\n")
            status.stringValue = "Folders selected, but they have not been enumerated and no content has been opened."
        } else {
            selectedFiles = Array(panel.urls.prefix(maxFiles))
            selectedFolders = []
            filesLabel.stringValue = selectedFiles.enumerated().map { "\($0.offset + 1). \($0.element.lastPathComponent)" }.joined(separator: "\n")
            status.stringValue = "Files named, but their content has not been opened."
        }
    }

    @objc private func selectOutput() {
        let panel = NSOpenPanel()
        panel.title = "Choose where 80Twenty may create the private job"
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK else { return }
        outputFolder = panel.url
        outputLabel.stringValue = panel.url?.path ?? "No folder selected."
    }

    @objc private func decline() {
        selectedFiles = []
        selectedFolders = []
        phrase.stringValue = ""
        acknowledgement.state = .off
        filesLabel.stringValue = "No files selected."
        status.stringValue = "Declined. No file content was read and no capability was created."
    }

    @objc private func approve() {
        var createdJob: URL?
        do {
            let enteredPhrase = phrase.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            guard acknowledgement.state == .on, enteredPhrase == confirmation else {
                throw BrokerError.message("The acknowledgement and exact confirmation phrase are required.")
            }
            let folderMode = scope.selectedSegment == 1
            guard folderMode ? !selectedFolders.isEmpty : !selectedFiles.isEmpty else {
                throw BrokerError.message(folderMode ? "Choose at least one folder." : "Choose at least one file.")
            }
            guard let parent = outputFolder else {
                throw BrokerError.message("Choose a private job folder.")
            }
            let jobID = UUID().uuidString.lowercased()
            let job = parent.appendingPathComponent("80Twenty-job-\(jobID)", isDirectory: true)
            createdJob = job
            let inputs = job.appendingPathComponent("inputs", isDirectory: true)
            let parentAccess = parent.startAccessingSecurityScopedResource()
            defer { if parentAccess { parent.stopAccessingSecurityScopedResource() } }
            try FileManager.default.createDirectory(at: inputs, withIntermediateDirectories: true,
                                                    attributes: [.posixPermissions: 0o700])

            var sourceFiles = selectedFiles
            var folderAccess: [URL] = []
            if folderMode {
                sourceFiles = []
                for folder in selectedFolders {
                    if folder.startAccessingSecurityScopedResource() { folderAccess.append(folder) }
                    guard let enumerator = FileManager.default.enumerator(
                        at: folder,
                        includingPropertiesForKeys: [.isRegularFileKey, .isSymbolicLinkKey],
                        options: [.skipsPackageDescendants]
                    ) else { throw BrokerError.message("A selected folder could not be enumerated.") }
                    for case let candidate as URL in enumerator {
                        if supportedExtensions.contains(candidate.pathExtension.lowercased()) {
                            sourceFiles.append(candidate)
                            if sourceFiles.count > maxFiles {
                                throw BrokerError.message("The job exceeds the 100,000-file emergency safety ceiling.")
                            }
                        }
                    }
                }
            }
            defer { folderAccess.forEach { $0.stopAccessingSecurityScopedResource() } }
            guard !sourceFiles.isEmpty else { throw BrokerError.message("No compatible text or image files were found.") }

            let personalDataAllowed = folderMode || sourceFiles.contains {
                imageExtensions.contains($0.pathExtension.lowercased())
            }

            var entries: [[String: Any]] = []
            var sourceTotal = 0
            var snapshotTotal = 0
            var imageCount = 0
            var excludedFileCount = 0
            var excludedReasons: [String: Int] = [:]
            var seenPaths = Set<String>()
            for source in sourceFiles {
                let canonicalPath = source.standardizedFileURL.resolvingSymlinksInPath().path
                if seenPaths.contains(canonicalPath) { continue }
                seenPaths.insert(canonicalPath)
                let access = folderMode ? false : source.startAccessingSecurityScopedResource()
                defer { if access { source.stopAccessingSecurityScopedResource() } }
                let sourceData: Data
                let snapshotData: Data
                let snapshotExtension: String
                let derivedFromImage: Bool
                do {
                    let values = try source.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
                    guard values.isRegularFile == true, values.isSymbolicLink != true else {
                        throw BrokerError.message("A selection is not a regular file or is a symbolic link.")
                    }
                    let ext = source.pathExtension.lowercased()
                    guard supportedExtensions.contains(ext) else {
                        throw BrokerError.message("Only supported text and image files are accepted.")
                    }
                    sourceData = try Data(contentsOf: source, options: [.mappedIfSafe])
                    if textExtensions.contains(ext) {
                        guard let decoded = String(data: sourceData, encoding: .utf8) else {
                            throw BrokerError.message("A selected text file is not UTF-8.")
                        }
                        let findings = privacyFindings(decoded, allowPersonalData: personalDataAllowed)
                        guard findings.isEmpty else {
                            throw BrokerError.message("Privacy scan rejected a selected file: \(findings.joined(separator: ", ")).")
                        }
                        snapshotData = sourceData
                        snapshotExtension = ext
                        derivedFromImage = false
                    } else {
                        let derivative = try localImageDerivative(sourceData)
                        let findings = privacyFindings(derivative, allowPersonalData: true)
                        guard findings.isEmpty else {
                            throw BrokerError.message("Privacy scan rejected an image derivative: \(findings.joined(separator: ", ")).")
                        }
                        snapshotData = Data(derivative.utf8)
                        snapshotExtension = "txt"
                        derivedFromImage = true
                    }
                } catch {
                    if folderMode {
                        excludedFileCount += 1
                        excludedReasons["unreadable_or_unsupported", default: 0] += 1
                        continue
                    }
                    throw error
                }
                sourceTotal += sourceData.count
                guard sourceTotal <= maxTotalBytes else {
                    throw BrokerError.message("Selected content exceeds the 10 GB emergency safety ceiling.")
                }
                snapshotTotal += snapshotData.count
                let name = String(format: "%06d.%@", entries.count, snapshotExtension)
                try snapshotData.write(to: inputs.appendingPathComponent(name), options: [.atomic])
                var entry: [String: Any] = [
                    "name": name, "bytes": snapshotData.count, "sha256": sha256(snapshotData),
                ]
                if derivedFromImage {
                    entry["derived_from"] = "image"
                    entry["source_media_sha256"] = sha256(sourceData)
                    imageCount += 1
                }
                entries.append(entry)
            }
            guard !entries.isEmpty else {
                throw BrokerError.message("No safe compatible files remained after local scanning.")
            }

            let created = Date()
            let disclosure = folderMode
                ? "80Twenty local training; every compatible text and image file in selected folders; personal data allowed; local image OCR and classification; no network; no real payment; withdrawal cannot untrain an existing model."
                : "80Twenty local training; exact selected text and image files; personal data allowed when images are selected; local image OCR and classification; no network; no real payment; withdrawal cannot untrain an existing model."
            let payload: [String: Any] = [
                "protocol": "kin/0.1",
                "type": "file_capability",
                "capability_version": "kin-file-capability/0.1",
                "job_id": jobID,
                "purpose": "local-model-training-poc",
                "granted": true,
                "interactive_confirmation": true,
                "interaction_channel": "macos_native",
                "created_at": isoDate(created),
                "expires_at": isoDate(created.addingTimeInterval(3600)),
                "files": entries,
                "total_input_bytes": snapshotTotal,
                "source_total_bytes": sourceTotal,
                "max_total_bytes": maxTotalBytes,
                "personal_data_allowed": personalDataAllowed,
                "image_data_allowed": imageCount > 0,
                "image_count": imageCount,
                "image_processing": imageCount == 0 ? "none" : "local_vision_ocr_classification_not_visual_finetuning",
                "external_network_allowed": false,
                "real_payment": false,
                "source_paths_recorded": false,
                "original_file_names_recorded": false,
                "excluded_file_count": excludedFileCount,
                "excluded_reason_counts": excludedReasons,
                "withdrawal_limit_acknowledged": true,
                "disclosure_sha256": sha256(Data(disclosure.utf8)),
            ]
            let key = try signingKey()
            let encoded = try canonicalJSON(payload)
            let signature = try key.signature(for: encoded)
            let record: [String: Any] = [
                "payload": payload,
                "public_key": key.publicKey.rawRepresentation.base64EncodedString(),
                "signature": signature.base64EncodedString(),
            ]
            let recordData = try JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
            try recordData.write(to: job.appendingPathComponent("capability.json"), options: [.atomic])
            status.stringValue = "Capability created for \(entries.count) files; \(excludedFileCount) unsafe or unreadable files excluded. No original names or paths were recorded. Job: \(job.path)"
        } catch {
            if let job = createdJob { try? FileManager.default.removeItem(at: job) }
            status.stringValue = "Not approved: \(error.localizedDescription)"
            NSSound.beep()
        }
    }
}

let application = NSApplication.shared
let delegate = AppDelegate()
application.delegate = delegate
application.run()
