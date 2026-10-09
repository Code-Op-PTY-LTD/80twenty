# Standalone participant consent architecture

KIN must not depend on a chat client. The participant experience should be a
small native companion application with a menu-bar or system-tray presence.
The application displays KIN-branded consent windows; it must not imitate an
operating-system security dialog because current operating systems do not have
a native "AI training" permission category.

## Required separation

```text
signed training job
        |
        v
KIN companion UI ---> participant approves or declines
        |                         |
        | approved scope          | decline: hard stop
        v
local consent broker + OS-protected signing key
        |
        | short-lived capability for exact files, purpose, model and job
        v
file-access broker ---> private transformation ---> sandboxed trainer
                                                   |
                                                   v
                                      signed adapter commitment
```

The generated worker must not receive blanket filesystem access. It receives a
short-lived capability and file handles from a separately maintained broker.
The capability names one job, purpose, model, data scope, byte ceiling and
expiry. A different job requires a new prompt.

## Participant flow

1. A job arrives without reading prospective data.
2. The companion app shows a blocking visual request with exact scope, purpose,
   outputs, network behaviour, compute limits, compensation, risks, expiry and
   withdrawal limitations.
3. The participant reviews individual files or a narrowly defined folder,
   chooses approve or decline, and enters an affirmative confirmation.
4. The consent broker signs the receipt using an OS-protected key.
5. The OS file picker grants only the selected handles to the file broker.
6. Preparation and training run locally with external networking denied.
7. The companion app shows progress, resource use, the resulting commitment,
   and controls to pause or delete local derivatives.

## Platform enforcement

- **macOS:** SwiftUI menu-bar app, App Sandbox, user-selected file entitlements,
  security-scoped bookmarks, and a signing key in Keychain/Secure Enclave.
- **Windows:** packaged desktop UI, AppContainer where practical, brokered file
  picker handles, DPAPI/TPM-backed identity and Windows notifications.
- **Linux:** portal file chooser, Flatpak or equivalent sandbox, Secret Service
  signing key and desktop notifications.
- **Headless systems:** a loopback-only page with a one-time session secret is a
  fallback. It is not the default consumer experience and remote approval is
  forbidden unless separately designed and authenticated.

## What the protocol can and cannot force

The protocol can reject contributions lacking a valid consent commitment and
the official client can deny file handles without one. A document alone cannot
prevent deliberately malicious software running with the user's full account
permissions from reading files. Strong enforcement therefore depends on the
separate broker, OS sandbox and independently reviewed client, not merely a
promise inside generated code.

## Growth path

Gate 1c implements the macOS proof as a native AppKit application. File
selection is mediated by `NSOpenPanel`, the signing key is stored in Keychain,
and a separately sandboxed compiled consumer receives only numbered snapshots
and a signed one-hour capability. Its sandbox denies network access, writes
outside the job and reads from user homes, external volumes and system
temporary-data folders. Tests prove an unrelated file cannot be read.

The participant can choose exact files or one or multiple folders. Folder mode
recursively enumerates every compatible `.md` and `.txt` file only after typed
approval and explicitly permits personal identifiers. Both modes reject
obvious credentials and private keys. A high emergency ceiling of 100,000 files
or 10 GB prevents accidental disk exhaustion without blocking ordinary folders.
Unsafe or unreadable folder entries are skipped without recording their names
or paths; the capability records only aggregate exclusion counts and reasons.

Before any personal-data pilot, replace deprecated `sandbox-exec` with a
separately signed App Sandbox helper or XPC service, add Developer ID signing
and notarisation, accessibility and localisation testing, revocation and
deletion receipts, leakage testing, and independent privacy and security
review.
