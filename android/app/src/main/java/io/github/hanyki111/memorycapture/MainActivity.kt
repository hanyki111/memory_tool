package io.github.hanyki111.memorycapture

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings as AndroidSettings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import io.github.hanyki111.memorycapture.core.CommandTemplate
import io.github.hanyki111.memorycapture.core.Entry
import io.github.hanyki111.memorycapture.core.Outcome
import io.github.hanyki111.memorycapture.core.PowerShell
import io.github.hanyki111.memorycapture.core.State
import io.github.hanyki111.memorycapture.core.Transitions
import io.github.hanyki111.memorycapture.data.EntryStore
import io.github.hanyki111.memorycapture.data.PhoneKey
import io.github.hanyki111.memorycapture.data.Settings
import io.github.hanyki111.memorycapture.send.Sender
import io.github.hanyki111.memorycapture.ssh.Ssh
import io.github.hanyki111.memorycapture.ui.AppTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** Settings, the phone's key, the PC's fingerprint, and the entries kept on the phone. */
class MainActivity : ComponentActivity() {

    private val askNotifications = registerForActivityResult(ActivityResultContracts.RequestPermission()) {}

    /** Counts returns to the screen, so what is set elsewhere, like the battery setting, is read again. */
    private val resumed = mutableIntStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= 33) askNotifications.launch(Manifest.permission.POST_NOTIFICATIONS)
        setContent { AppTheme { MainScreen(resumed.intValue) } }
    }

    override fun onResume() {
        super.onResume()
        resumed.intValue++
    }
}

@Composable
private fun MainScreen(resumed: Int) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    val scope = rememberCoroutineScope()

    var host by remember { mutableStateOf(settings.host) }
    var port by remember { mutableStateOf(settings.port.toString()) }
    var user by remember { mutableStateOf(settings.user) }
    var template by remember { mutableStateOf(settings.template) }
    var delay by remember { mutableStateOf(settings.voiceDelaySeconds.toString()) }
    var fingerprint by remember { mutableStateOf(settings.fingerprint) }
    var publicKey by remember { mutableStateOf("") }

    var dialog by remember { mutableStateOf<Pair<String, String>?>(null) } // title, body
    var offeredFingerprint by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }

    // Redraw the lists whenever the stored entries change.
    var version by remember { mutableIntStateOf(0) }
    DisposableEffect(Unit) {
        val listener = { version++ ; Unit }
        EntryStore.listen(listener)
        onDispose { EntryStore.unlisten(listener) }
    }
    val entries = remember(version) { EntryStore.all(context) }

    // Made on first use, which takes a moment, so not on the main thread.
    LaunchedEffect(Unit) { publicKey = withContext(Dispatchers.IO) { PhoneKey(context).publicKeyLine() } }

    val templateError = CommandTemplate.parse(template).exceptionOrNull()?.message

    fun save() {
        settings.host = host
        settings.port = port.toIntOrNull() ?: 22
        settings.user = user
        if (templateError == null) settings.template = template
        settings.voiceDelaySeconds = delay.toIntOrNull() ?: 3
    }

    Scaffold { inner ->
        Column(
            Modifier.fillMaxSize().padding(inner).padding(16.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineSmall)

            Button(onClick = { context.startActivity(Intent(context, CaptureActivity::class.java)) }, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.main_new_entry))
            }

            EntrySections(entries, onSendNow = { Sender.schedule(context) })

            HorizontalDivider()
            Text(stringResource(R.string.main_pc), style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(host, { host = it }, label = { Text(stringResource(R.string.main_host)) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(port, { port = it }, label = { Text(stringResource(R.string.main_port)) }, modifier = Modifier.weight(1f), singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number))
                OutlinedTextField(user, { user = it }, label = { Text(stringResource(R.string.main_user)) }, modifier = Modifier.weight(2f), singleLine = true)
            }
            OutlinedTextField(
                template, { template = it },
                label = { Text(stringResource(R.string.main_command)) },
                supportingText = { Text(templateError ?: stringResource(R.string.main_command_help)) },
                isError = templateError != null,
                modifier = Modifier.fillMaxWidth(),
                textStyle = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
            )
            OutlinedTextField(delay, { delay = it }, label = { Text(stringResource(R.string.main_voice_delay)) }, singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number))
            Button(onClick = { save(); dialog = context.getString(R.string.main_saved) to "" }) { Text(stringResource(R.string.save)) }

            HorizontalDivider()
            Text(stringResource(R.string.main_key), style = MaterialTheme.typography.titleMedium)
            Text(stringResource(R.string.main_key_help), style = MaterialTheme.typography.bodySmall)
            SelectionContainer { Text(publicKey, style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace)) }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { copy(context, publicKey) }) { Text(stringResource(R.string.copy)) }
                OutlinedButton(onClick = { share(context, publicKey) }) { Text(stringResource(R.string.share)) }
            }

            HorizontalDivider()
            Text(stringResource(R.string.main_fingerprint), style = MaterialTheme.typography.titleMedium)
            Text(
                if (fingerprint.isEmpty()) stringResource(R.string.main_fingerprint_none) else "SHA256:$fingerprint",
                style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(enabled = !busy, onClick = {
                    save()
                    val target = settings.target() ?: run { dialog = context.getString(R.string.main_fill_pc) to ""; return@OutlinedButton }
                    busy = true
                    scope.launch {
                        val result = withContext(Dispatchers.IO) { Ssh.fingerprint(target) }
                        busy = false
                        result.fold({ offeredFingerprint = it }, { dialog = context.getString(R.string.main_failed) to (it.message ?: "") })
                    }
                }) { Text(stringResource(R.string.main_get_fingerprint)) }

                OutlinedButton(enabled = !busy && fingerprint.isNotEmpty(), onClick = {
                    save()
                    busy = true
                    scope.launch {
                        dialog = context.getString(R.string.main_test) to withContext(Dispatchers.IO) { testConnection(context) }
                        busy = false
                    }
                }) { Text(stringResource(R.string.main_test)) }
            }
            HorizontalDivider()
            BatterySection(resumed)
            Spacer(Modifier.padding(24.dp))
        }
    }

    offeredFingerprint?.let { offered ->
        AlertDialog(
            onDismissRequest = { offeredFingerprint = null },
            title = { Text(stringResource(R.string.main_trust_title)) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(stringResource(R.string.main_trust_body))
                    SelectionContainer { Text("SHA256:$offered", fontFamily = FontFamily.Monospace) }
                }
            },
            confirmButton = {
                TextButton(onClick = { settings.fingerprint = offered; fingerprint = offered; offeredFingerprint = null }) {
                    Text(stringResource(R.string.main_trust))
                }
            },
            dismissButton = { TextButton(onClick = { offeredFingerprint = null }) { Text(stringResource(R.string.cancel)) } },
        )
    }

    dialog?.let { (title, body) ->
        AlertDialog(
            onDismissRequest = { dialog = null },
            title = { Text(title) },
            text = if (body.isEmpty()) null else ({ SelectionContainer { Text(body) } }),
            confirmButton = { TextButton(onClick = { dialog = null }) { Text(stringResource(R.string.ok)) } },
        )
    }
}

@Composable
private fun EntrySections(entries: List<Entry>, onSendNow: () -> Unit) {
    val context = LocalContext.current
    val attention = entries.filter { it.state == State.ATTENTION }
    val pending = entries.filter { it.state == State.PENDING }
    val sent = entries.filter { it.state == State.SENT }.sortedByDescending { it.changedAt }.take(10)

    if (attention.isNotEmpty()) {
        Text(stringResource(R.string.main_attention, attention.size), style = MaterialTheme.typography.titleMedium)
        attention.forEach { entry ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("${entry.date} ${entry.time}  ${entry.text}")
                    Text(
                        if (entry.maybeRecorded) stringResource(R.string.main_maybe_recorded) else entry.note,
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        TextButton(onClick = { EntryStore.put(context, Transitions.markSent(entry, System.currentTimeMillis())) }) {
                            Text(stringResource(R.string.main_mark_sent))
                        }
                        TextButton(onClick = {
                            EntryStore.put(context, Transitions.resend(entry, System.currentTimeMillis()))
                            Sender.schedule(context)
                        }) { Text(stringResource(R.string.main_resend)) }
                        TextButton(onClick = { EntryStore.remove(context, entry.id) }) { Text(stringResource(R.string.delete)) }
                    }
                }
            }
        }
    }

    if (pending.isNotEmpty()) {
        Text(stringResource(R.string.main_pending, pending.size), style = MaterialTheme.typography.titleMedium)
        pending.sortedWith(compareBy({ it.date }, { it.time })).forEach {
            Column {
                Text("${it.date} ${it.time}  ${it.text}", style = MaterialTheme.typography.bodyMedium)
                Text(
                    if (it.attempts == 0) stringResource(R.string.main_not_tried)
                    else stringResource(R.string.main_last_try, whenTried(it.changedAt), it.note),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        OutlinedButton(onClick = onSendNow) { Text(stringResource(R.string.main_send_now)) }
    }

    if (sent.isNotEmpty()) {
        Text(stringResource(R.string.main_sent), style = MaterialTheme.typography.titleMedium)
        sent.forEach { Text("${it.date} ${it.time}  ${it.text}", style = MaterialTheme.typography.bodySmall) }
    }
}

/**
 * Android may hold back background sending to save battery, Samsung phones
 * especially. Says whether the app is exempt, and opens the setting.
 */
@Composable
private fun BatterySection(resumed: Int) {
    val context = LocalContext.current
    val unrestricted = remember(resumed) {
        context.getSystemService(PowerManager::class.java).isIgnoringBatteryOptimizations(context.packageName)
    }
    Text(stringResource(R.string.main_battery), style = MaterialTheme.typography.titleMedium)
    Text(
        stringResource(if (unrestricted) R.string.main_battery_unrestricted else R.string.main_battery_restricted),
        style = MaterialTheme.typography.bodySmall,
    )
    OutlinedButton(onClick = {
        val details = Intent(AndroidSettings.ACTION_APPLICATION_DETAILS_SETTINGS, "package:${context.packageName}".toUri())
        context.startActivity(details)
    }) { Text(stringResource(R.string.main_battery_open)) }
}

/** HH:mm today, or MM-dd HH:mm on another day. */
private fun whenTried(millis: Long): String {
    val at = Instant.ofEpochMilli(millis).atZone(ZoneId.systemDefault())
    val pattern = if (at.toLocalDate() == LocalDate.now()) "HH:mm" else "MM-dd HH:mm"
    return at.format(DateTimeFormatter.ofPattern(pattern))
}

/** Run `memory_tool --version` through the saved command, and say what came back. */
private fun testConnection(context: Context): String {
    val settings = Settings(context)
    val target = settings.target() ?: return context.getString(R.string.main_fill_pc)
    val template = CommandTemplate.parse(settings.template).getOrElse { return it.message ?: "" }
    val command = PowerShell.forTransport(template.fill(listOf("--version")))
    return when (val outcome = Ssh.run(target, PhoneKey(context).get(), settings.fingerprint, command)) {
        is Outcome.NotSent -> outcome.reason
        is Outcome.Uncertain -> outcome.reason
        is Outcome.Ran -> (outcome.stdout + outcome.stderr).trim().ifEmpty { "exit ${outcome.exitStatus}" }
    }
}

private fun copy(context: Context, text: String) {
    context.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("ssh key", text))
}

private fun share(context: Context, text: String) {
    val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text)
    context.startActivity(Intent.createChooser(send, null))
}
