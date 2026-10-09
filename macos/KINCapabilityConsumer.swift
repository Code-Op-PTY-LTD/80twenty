import CryptoKit
import Foundation

enum ConsumerError: Error, CustomStringConvertible {
    case invalid(String)
    var description: String { switch self { case .invalid(let value): return value } }
}

func canonicalJSON(_ value: Any) throws -> Data {
    try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
}

func hash(_ data: Data) -> String {
    SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}

func privacyFindings(_ text: String, allowPersonalData: Bool) -> [String] {
    var patterns = [
        ("private_key", "-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        ("cloud_access_key", "\\b(AKIA|ASIA)[A-Z0-9]{16}\\b"),
        ("secret_assignment", "(?i)\\b(api[_-]?key|access[_-]?token|password|passwd|secret)\\s*[:=]\\s*[^\\s]{6,}"),
    ]
    if !allowPersonalData {
        patterns.append(("email_address", "(?i)\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b"))
        patterns.append(("phone_number_like_text", "(?<!\\w)(\\+?\\d[\\d ()-]{7,}\\d)(?!\\w)"))
    }
    let range = NSRange(text.startIndex..<text.endIndex, in: text)
    return patterns.compactMap { label, pattern in
        (try? NSRegularExpression(pattern: pattern))?.firstMatch(in: text, range: range) == nil ? nil : label
    }
}

func markdownSections(_ text: String) -> [(String, String)] {
    var sections: [(String, String)] = []
    var heading = "Document introduction"
    var paragraph: [String] = []
    var fenced = false
    func cleaned(_ lines: [String]) -> String {
        lines.map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }.joined(separator: " ")
            .replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
    func headingValue(_ line: String) -> String? {
        guard let regex = try? NSRegularExpression(pattern: "^#{1,6}\\s+(.+?)\\s*$") else { return nil }
        let range = NSRange(line.startIndex..<line.endIndex, in: line)
        guard let match = regex.firstMatch(in: line, range: range), let capture = Range(match.range(at: 1), in: line) else { return nil }
        return String(line[capture]).trimmingCharacters(in: .whitespaces)
    }
    func flush() {
        let value = cleaned(paragraph)
        if value.count >= 40 && value.count <= 700 { sections.append((heading, value)) }
        paragraph = []
    }
    for line in text.components(separatedBy: .newlines) {
        if line.trimmingCharacters(in: .whitespaces).hasPrefix("```") { flush(); fenced.toggle(); continue }
        if fenced { continue }
        if let value = headingValue(line) { flush(); heading = value; continue }
        if line.trimmingCharacters(in: .whitespaces).isEmpty { flush(); continue }
        let left = line.trimmingCharacters(in: .whitespaces)
        if left.hasPrefix("|") || left.hasPrefix("- ") || left.hasPrefix("* ") || left.hasPrefix(">") { flush(); continue }
        paragraph.append(line)
    }
    flush()
    return sections
}

func writeJSONL(_ url: URL, _ rows: [[String: String]]) throws {
    var output = Data()
    for row in rows {
        output.append(try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys]))
        output.append(0x0a)
    }
    try output.write(to: url, options: .atomic)
}

func consume(_ job: URL) throws -> [String: Any] {
    let capabilityURL = job.appendingPathComponent("capability.json")
    let recordObject = try JSONSerialization.jsonObject(with: Data(contentsOf: capabilityURL))
    guard let record = recordObject as? [String: Any],
          let payload = record["payload"] as? [String: Any],
          let publicText = record["public_key"] as? String,
          let signatureText = record["signature"] as? String,
          let publicData = Data(base64Encoded: publicText),
          let signature = Data(base64Encoded: signatureText) else {
        throw ConsumerError.invalid("capability envelope is malformed")
    }
    let key = try Curve25519.Signing.PublicKey(rawRepresentation: publicData)
    guard key.isValidSignature(signature, for: try canonicalJSON(payload)) else {
        throw ConsumerError.invalid("capability signature is invalid")
    }
    let interactionChannel = payload["interaction_channel"] as? String
    let validInteraction = interactionChannel == "macos_native" ||
        (interactionChannel == "macos_native_recovery" && payload["recovered_from_interrupted_native_broker"] as? Bool == true)
    guard payload["protocol"] as? String == "kin/0.1",
          payload["type"] as? String == "file_capability",
          payload["capability_version"] as? String == "kin-file-capability/0.1",
          payload["purpose"] as? String == "local-model-training-poc",
          payload["granted"] as? Bool == true,
          payload["interactive_confirmation"] as? Bool == true,
          validInteraction,
          payload["external_network_allowed"] as? Bool == false,
          payload["source_paths_recorded"] as? Bool == false,
          payload["original_file_names_recorded"] as? Bool == false else {
        throw ConsumerError.invalid("capability scope is not authorised")
    }
    let expiryFormatter = ISO8601DateFormatter()
    expiryFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    guard let personalDataAllowed = payload["personal_data_allowed"] as? Bool else {
        throw ConsumerError.invalid("personal-data scope is not explicit")
    }
    guard let expiryText = payload["expires_at"] as? String,
          let expiry = expiryFormatter.date(from: expiryText), expiry > Date() else {
        throw ConsumerError.invalid("capability has expired")
    }
    guard let files = payload["files"] as? [[String: Any]], files.count >= 1, files.count <= 100_000,
          let ceiling = payload["max_total_bytes"] as? Int, ceiling > 0, ceiling <= 10_000_000_000,
          let declaredTotal = payload["total_input_bytes"] as? Int else {
        throw ConsumerError.invalid("capability limits are invalid")
    }

    let inputs = job.appendingPathComponent("inputs", isDirectory: true)
    var seen = Set<String>()
    var total = 0
    var sections: [(String, String)] = []
    var commitments: [[String: Any]] = []
    for (index, file) in files.enumerated() {
        guard let name = file["name"] as? String, URL(fileURLWithPath: name).lastPathComponent == name,
              !seen.contains(name), ["md", "txt"].contains(URL(fileURLWithPath: name).pathExtension.lowercased()),
              let bytes = file["bytes"] as? Int, let digest = file["sha256"] as? String else {
            throw ConsumerError.invalid("snapshot entry is invalid")
        }
        let url = inputs.appendingPathComponent(name)
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
        guard values.isRegularFile == true, values.isSymbolicLink != true else { throw ConsumerError.invalid("snapshot is absent or linked") }
        let data = try Data(contentsOf: url)
        guard data.count == bytes, hash(data) == digest else { throw ConsumerError.invalid("snapshot commitment mismatch") }
        guard let text = String(data: data, encoding: .utf8) else { throw ConsumerError.invalid("snapshot is not UTF-8") }
        let findings = privacyFindings(text, allowPersonalData: personalDataAllowed)
        guard findings.isEmpty else { throw ConsumerError.invalid("privacy scan rejected snapshot: \(findings.joined(separator: ","))") }
        let localSections = markdownSections(text)
        sections.append(contentsOf: localSections)
        commitments.append(["logical_index": index, "bytes": data.count, "sha256": digest, "sections": localSections.count])
        total += data.count
        seen.insert(name)
    }
    guard total == declaredTotal, total <= ceiling else { throw ConsumerError.invalid("snapshot total violates scope") }
    guard sections.count >= 8 else { throw ConsumerError.invalid("too few usable sections") }

    var train: [[String: String]] = []
    var hidden: [[String: String]] = []
    for (index, section) in sections.enumerated() {
        let label = String(format: "local-section-%03d", index)
        train.append(["prompt": "In the authorised local knowledge set, reproduce \(label) titled '\(section.0)'.", "completion": section.1])
        train.append(["prompt": "Recall the exact local note \(label), whose heading is '\(section.0)'.", "completion": section.1])
        hidden.append(["prompt": "From the consented local corpus, provide the content of \(label) under '\(section.0)'.", "completion": section.1])
    }
    let validCount = max(4, min(train.count / 10, 24))
    let derived = job.appendingPathComponent("derived", isDirectory: true)
    var isDirectory: ObjCBool = false
    if FileManager.default.fileExists(atPath: derived.path, isDirectory: &isDirectory) {
        guard isDirectory.boolValue else { throw ConsumerError.invalid("derived output is not a directory") }
    } else {
        try FileManager.default.createDirectory(at: derived, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
    }
    try writeJSONL(derived.appendingPathComponent("train.jsonl"), train)
    try writeJSONL(derived.appendingPathComponent("valid.jsonl"), Array(train.prefix(validCount)))
    try writeJSONL(derived.appendingPathComponent("test.jsonl"), hidden)
    let dataset = try Data(contentsOf: derived.appendingPathComponent("train.jsonl"))
        + Data(contentsOf: derived.appendingPathComponent("valid.jsonl"))
        + Data(contentsOf: derived.appendingPathComponent("test.jsonl"))
    guard let jobID = payload["job_id"] as? String else { throw ConsumerError.invalid("job id is absent") }
    var receipt: [String: Any] = [
        "protocol": "kin/0.1", "type": "capability_dataset_receipt",
        "job_id_sha256": hash(Data(jobID.utf8)), "created_at": ISO8601DateFormatter().string(from: Date()),
        "purpose": "local-model-training-poc", "file_count": files.count,
        "total_input_bytes": total, "input_commitments": commitments,
        "section_count": sections.count, "train_examples": train.count,
        "validation_examples": validCount, "hidden_examples": hidden.count,
        "dataset_sha256": hash(dataset), "raw_text_in_receipt": false,
        "source_paths_in_capability": false, "personal_data_allowed": personalDataAllowed,
        "network_used": false, "native_broker": true,
    ]
    receipt["receipt_sha256"] = hash(try canonicalJSON(receipt))
    try JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
        .write(to: derived.appendingPathComponent("dataset-receipt.json"), options: .atomic)
    return receipt
}

do {
    guard CommandLine.arguments.count == 3, CommandLine.arguments[1] == "--job-dir" else {
        throw ConsumerError.invalid("usage: kin-capability-consumer --job-dir PATH")
    }
    let receipt = try consume(URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true).standardizedFileURL)
    let summary: [String: Any] = ["dataset_sha256": receipt["dataset_sha256"]!, "file_count": receipt["file_count"]!, "train_examples": receipt["train_examples"]!, "sandboxed": true]
    print(String(data: try canonicalJSON(summary), encoding: .utf8)!)
} catch {
    FileHandle.standardError.write(Data("KIN capability consumer failed: \(error)\n".utf8))
    exit(2)
}
