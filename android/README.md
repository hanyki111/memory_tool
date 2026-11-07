# Memory Capture (Android)

Record to the [memory_tool](https://github.com/hanyki111/memory_tool) timeline from an Android phone, and read,
search and edit it. The app runs memory_tool on the PC over SSH for everything, so every entry goes through the same
CLI as the PC's own `m`. Entries written without a connection wait on the phone and are sent later, at the time they
were written. Nothing of the PC's timeline is stored on the phone, except the three latest entries while the large widget
shows them.

Needs memory_tool 1.6.0 or later on the PC (`entry find/edit/delete`).

## The timeline

The app opens on the PC's timeline, newest first, a week at a time; scroll to the end for the week before, pull down
to refresh. Touch and hold an entry to change its text, date or time, or to delete it (`entry edit`,
`entry delete`); a tap only says so, since editing is rare. The
entry is named by its date, time and text as listed; if it changed on the PC meanwhile, nothing changes and the day
is loaded again. The search field finds timeline entries by keyword (`ms --type timeline`).

Each day is a line with a dot per entry; the newest of the day has the accent's dot. Tags written before the text
(`[idea] …`) show as chips; the entry itself is not changed. The field at the bottom sends at once; the microphone
fills it with speech. Entries not yet on the PC are folded
into a line just above the field, with their count and the latest one; tap it to open them. The gear opens the
settings. **Look:** light, dark or as the phone; the accent, from the wallpaper (Android 12 and later) or one of six;
the text size, 70 to 200 percent of the phone's own. The widget and the small capture window follow the light or dark
and the accent; the widget's text size follows the phone's.

## The small capture window

- **Quick settings tile:** pull down the notification shade, edit the tiles, and add **Record**
- **Home screen widgets**, three to choose from:
  - **Record (small)**, 1x1: a round button that opens the window.
  - **Record**, 4x1: looks like a text field; the microphone starts speech input. It also shows entries waiting to be
    sent or to be checked. (Android widgets cannot hold a text field, so tapping it opens the window.)
  - **Record and latest entries**, 4x2: the same field with the PC's three latest entries below it; tapping them
    opens the timeline. They are fetched every 30 minutes (with a network), when the app loads the timeline and
    after an entry reaches the PC; the widget says when. These few entries are the only part of the PC's timeline
    kept on the phone, only while such a widget is on the home screen, and never in a backup.
- **Share:** choose **Record to timeline** in another app's share sheet
- **App shortcuts:** touch and hold the app icon for **Record** and **Record by voice**. Samsung's Modes and Routines
  lists them as app actions, so a routine can open the window, or open it listening.

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

1. **PC:** address (DDNS name or IP), port and user.
2. **Knowledge base folder:** the folder where you run `m` on the PC, such as `E:\notes`. Save. The app runs

   ```text
   Set-Location -LiteralPath 'E:\notes' -ErrorAction Stop; python -m memory_tool <arguments>
   ```

   A wrong folder stops there, so memory_tool never runs in the SSH session's home folder instead. `python` must be
   on the PATH of the PC's SSH sessions. A command saved by 0.2 or earlier gives its folder to this field.
3. **Get fingerprint**, compare it with the PC's, and trust it only if they match. A PC with any other fingerprint is
   refused before anything is sent.
4. **Test connection** runs `memory_tool --version` and `base show` in that folder.

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
- A send that certainly did not reach the PC is first tried again within the same work, after 5, 10 and 20 seconds:
  right after a network appears its DNS may not answer yet. After that it waits and is tried again after 15 seconds, then
  30, 45 and so on, never more than 5 minutes apart. The list of waiting entries shows the last try and its reason.
- Battery optimization, which Samsung phones apply strongly, can still hold background work back. The app's
  **Battery** section says whether the app is exempt and opens its settings, where **Unrestricted** removes the limit.
- A send that broke after the command went out, as when the phone moves from mobile data to Wi-Fi, may already be on
  the PC. The app then asks the PC with `entry find`, which compares after writing tags as `record` does (it turns
  `fix #bug` into `[bug] fix`): found means sent, absent means it is sent again, so nothing is recorded twice. Two
  identical entries written in the same minute would look like one. An older memory_tool without `entry` leaves the
  entry to check rather than sending it again. Only when the answer cannot be read is the entry marked **to check**: look at the PC's timeline and
  choose **It is recorded** or **Send again**. memory_tool refusals, such as `distant_past`, are also left to check.
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

Reading the timeline without a connection, semantic search, editing documents, several PCs, Play Store
distribution.
