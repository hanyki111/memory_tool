# Memory Capture (Android)

Record to the [memory_tool](https://github.com/hanyki111/memory_tool) timeline from an Android phone. The app sends
each entry over SSH to the PC, where `python -m memory_tool record` writes it, so every entry goes through the same
CLI as the PC's own `m`. Entries written without a connection wait on the phone and are sent later, at the time they
were written.

## Opening the capture window

- **App icon**, then **New entry**
- **Quick settings tile:** pull down the notification shade, edit the tiles, and add **Record**
- **Home screen widget:** looks like a text field; the microphone starts speech input. It also shows entries waiting
  to be sent or to be checked. (Android widgets cannot hold a text field, so tapping it opens the window.)
- **Share:** choose **Record to timeline** in another app's share sheet

Speech is shown for a few seconds before sending (set in the app); tap the text to edit it instead.

## Setting up

### On the PC (Windows, OpenSSH server)

1. The OpenSSH server must be running and reachable, for example through a port forward and a DDNS name.
2. Add the phone's public key, shown in the app under **This phone's key**, to the authorized keys. For an
   account in the Administrators group, Windows OpenSSH reads `C:\ProgramData\ssh\administrators_authorized_keys`
   (not `~\.ssh\authorized_keys`), and that file must be limited to Administrators and SYSTEM. In an administrator
   PowerShell:

   ```powershell
   $keys = "C:\ProgramData\ssh\administrators_authorized_keys"
   Add-Content -Path $keys -Encoding ascii -Value "ssh-ed25519 AAAA... memory-capture@phone"
   icacls $keys /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
   ```

3. Note the PC's host key fingerprint, to compare in the app:

   ```powershell
   ssh-keygen -lf C:\ProgramData\ssh\ssh_host_ed25519_key.pub
   ```

### In the app

1. **PC:** address (DDNS name or IP), port and user. Save.
2. **Command:** how PowerShell on the PC runs memory_tool, with `{args}` where the app puts the arguments. For
   example:

   ```text
   Set-Location 'E:\code_projects\memory_notion'; python -m memory_tool {args}
   ```

   `Set-Location` chooses the knowledge base. Use the full path of Python if `python` is not on the PC's PATH.
3. **Get fingerprint**, compare it with the PC's, and trust it only if they match. A PC with any other fingerprint is
   refused before anything is sent.
4. **Test connection** runs `memory_tool --version` through the command.

## How sending works

- The app quotes every argument as a PowerShell single-quoted string, where nothing is expanded; typographic quotes
  (`‘ ’`), which phone keyboards insert, count as quotes too and are doubled. The whole command then travels as
  Base64 that PowerShell decodes and runs with UTF-8 output. The Windows command line that OpenSSH builds takes
  double quotes apart and depends on code pages; Base64 passes through it unchanged.
- Each entry is sent as `record --json --date <written> --time <written> -- <text>`, so a late entry keeps its time,
  and text starting with `-` stays text.
- While entries are waiting, the app asks Android to wake it when a validated network appears (a network callback
  with a PendingIntent), so turning airplane mode off sends them without opening the app. Sending runs as expedited
  work, which Android starts promptly in the background. Sends run one at a time, so no entry is sent twice at once.
- A send that certainly did not reach the PC (no network, PC off) waits and is tried again after 15 seconds, then
  30, 45 and so on, never more than 5 minutes apart. The list of waiting entries shows the last try and its reason.
- Battery optimization, which Samsung phones apply strongly, can still hold background work back. The app's
  **Battery** section says whether the app is exempt and opens its settings, where **Unrestricted** removes the limit.
- A send that broke after the command went out is marked **to check**: open the app, look at the PC's timeline, and choose
  **It is recorded** or **Send again**. memory_tool refusals, such as `distant_past`, are also left to check.
- The PC refusing the key, a changed fingerprint, or missing settings are reported once as a notification; waiting
  will not fix them.

## Security

- The phone makes its own Ed25519 key. The private key is sealed with an AES key in the Android Keystore that never
  leaves the device, and app data is excluded from backups and device-to-device transfers. A new phone makes a new
  key, to be registered on the PC; remove a lost phone's line from the authorized keys.
- Only public key login is tried; the app never sends a password.
- The PC is trusted by one fingerprint, confirmed by the person.

## Building

Requirements: JDK 17 and the Android SDK (platform 36, build tools). `local.properties` (not committed) points at
them and at the release signing key:

```properties
sdk.dir=E\:/dev/android-sdk
capture.signing=E\:/dev/keys/memory-capture.properties
```

The signing properties file holds `storeFile`, `storePassword`, `keyAlias` and `keyPassword`. **Keep the key**:
every update must be signed with it, or Android will not install it over the old version.

```powershell
$env:JAVA_HOME = 'E:\dev\jdk-17'
.\gradlew testDebugUnitTest   # JVM tests: quoting, replies, the queue, SSH against Apache MINA sshd,
                              # and, where pwsh and python exist, the whole way into this checkout's memory_tool
.\gradlew assembleRelease     # app\build\outputs\apk\release\app-release.apk
```

Copy the APK to the phone and open it. Play Protect may warn about an app from an unknown developer; choose to
install anyway.

## Not in this version

Reading or editing the timeline (planned for 0.2), editing documents, several PCs, Play Store distribution.
