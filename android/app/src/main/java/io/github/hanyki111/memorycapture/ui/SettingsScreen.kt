@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package io.github.hanyki111.memorycapture.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.PowerManager
import android.provider.Settings as AndroidSettings
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import io.github.hanyki111.memorycapture.R
import io.github.hanyki111.memorycapture.core.Accent
import io.github.hanyki111.memorycapture.core.KnowledgeBase
import io.github.hanyki111.memorycapture.core.Mode
import io.github.hanyki111.memorycapture.core.Outcome
import io.github.hanyki111.memorycapture.core.PowerShell
import io.github.hanyki111.memorycapture.data.PhoneKey
import io.github.hanyki111.memorycapture.data.Settings
import io.github.hanyki111.memorycapture.ssh.Ssh
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.roundToInt

/** The look, the PC and its knowledge base, voice, the phone's key, and battery; one group each. */
@Composable
fun SettingsScreen(
    resumed: Int,
    fontPercent: Int,
    onFontPercent: (Int) -> Unit,
    mode: Mode,
    onMode: (Mode) -> Unit,
    accent: Accent,
    onAccent: (Accent) -> Unit,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    val scope = rememberCoroutineScope()

    var host by remember { mutableStateOf(settings.host) }
    var port by remember { mutableStateOf(settings.port.toString()) }
    var user by remember { mutableStateOf(settings.user) }
    var basePath by remember { mutableStateOf(settings.basePath) }
    var delay by remember { mutableStateOf(settings.voiceDelaySeconds.toString()) }
    var fingerprint by remember { mutableStateOf(settings.fingerprint) }
    var publicKey by remember { mutableStateOf("") }

    var dialog by remember { mutableStateOf<Pair<String, String>?>(null) } // title, body
    var offeredFingerprint by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }

    // Made on first use, which takes a moment, so not on the main thread.
    LaunchedEffect(Unit) { publicKey = withContext(Dispatchers.IO) { PhoneKey(context).publicKeyLine() } }

    val baseProblem = KnowledgeBase.problem(basePath)

    fun save() {
        settings.host = host
        settings.port = port.toIntOrNull() ?: 22
        settings.user = user
        if (baseProblem == null) settings.basePath = basePath
        settings.voiceDelaySeconds = delay.toIntOrNull() ?: 3
    }

    Scaffold(topBar = {
        Row(Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 4.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = { save(); onBack() }) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.back))
            }
            Text(stringResource(R.string.settings), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        }
    }) { inner ->
        Column(
            Modifier.fillMaxSize().padding(inner).verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp).navigationBarsPadding(),
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            Group(stringResource(R.string.section_look)) {
                Label(stringResource(R.string.mode_title))
                ModeChoice(mode, onMode)
                Label(stringResource(R.string.accent_title))
                AccentChoice(accent, onAccent)
                Label(stringResource(R.string.font_size))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Slider(
                        value = fontPercent.toFloat(),
                        onValueChange = { onFontPercent(((it / 10f).roundToInt() * 10)) },
                        valueRange = Settings.FONT_MIN.toFloat()..Settings.FONT_MAX.toFloat(),
                        steps = (Settings.FONT_MAX - Settings.FONT_MIN) / 10 - 1,
                        modifier = Modifier.weight(1f),
                    )
                    Text("$fontPercent%", style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(start = 12.dp))
                }
                Text(stringResource(R.string.font_preview), style = MaterialTheme.typography.bodyLarge)
            }

            Group(stringResource(R.string.main_pc)) {
                OutlinedTextField(host, { host = it }, label = { Text(stringResource(R.string.main_host)) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(port, { port = it }, label = { Text(stringResource(R.string.main_port)) }, modifier = Modifier.weight(1f), singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number))
                    OutlinedTextField(user, { user = it }, label = { Text(stringResource(R.string.main_user)) }, modifier = Modifier.weight(2f), singleLine = true)
                }
                OutlinedTextField(
                    basePath, { basePath = it },
                    label = { Text(stringResource(R.string.main_base)) },
                    placeholder = { Text("E:\\notes") },
                    supportingText = { Text(if (basePath.isEmpty() || baseProblem == null) stringResource(R.string.main_base_help) else baseProblem) },
                    isError = basePath.isNotEmpty() && baseProblem != null,
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Button(onClick = { save(); dialog = context.getString(R.string.main_saved) to "" }) { Text(stringResource(R.string.save)) }

                Label(stringResource(R.string.main_fingerprint))
                Text(
                    if (fingerprint.isEmpty()) stringResource(R.string.main_fingerprint_none) else "SHA256:$fingerprint",
                    style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
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
            }

            Group(stringResource(R.string.section_voice)) {
                OutlinedTextField(delay, { delay = it; delay.toIntOrNull()?.let { s -> settings.voiceDelaySeconds = s } },
                    label = { Text(stringResource(R.string.main_voice_delay)) }, singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth())
            }

            Group(stringResource(R.string.main_key)) {
                Text(stringResource(R.string.main_key_help), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                SelectionContainer { Text(publicKey, style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace)) }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { copy(context, publicKey) }) { Text(stringResource(R.string.copy)) }
                    OutlinedButton(onClick = { share(context, publicKey) }) { Text(stringResource(R.string.share)) }
                }
            }

            Group(stringResource(R.string.main_battery)) { BatterySection(resumed) }
            Spacer(Modifier.height(24.dp))
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

/** A titled group on a raised, rounded surface. */
@Composable
private fun Group(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            title,
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 4.dp),
        )
        Column(
            Modifier.fillMaxWidth()
                .background(MaterialTheme.colorScheme.surfaceContainer, RoundedCornerShape(20.dp))
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            content = content,
        )
    }
}

@Composable
private fun Label(text: String) {
    Text(text, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ModeChoice(mode: Mode, onMode: (Mode) -> Unit) {
    val labels = mapOf(
        Mode.SYSTEM to R.string.mode_system,
        Mode.LIGHT to R.string.mode_light,
        Mode.DARK to R.string.mode_dark,
    )
    SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
        Mode.entries.forEachIndexed { i, m ->
            SegmentedButton(
                selected = m == mode,
                onClick = { onMode(m) },
                shape = SegmentedButtonDefaults.itemShape(i, Mode.entries.size),
            ) { Text(stringResource(labels.getValue(m)), maxLines = 1) }
        }
    }
}

/** A row of swatches; the phone's own colour first where the phone has one. */
@Composable
private fun AccentChoice(accent: Accent, onAccent: (Accent) -> Unit) {
    val context = LocalContext.current
    val dark = MaterialTheme.colorScheme.background.luminance() < 0.5f
    val names = mapOf(
        Accent.DYNAMIC to R.string.accent_dynamic,
        Accent.INDIGO to R.string.accent_indigo,
        Accent.TEAL to R.string.accent_teal,
        Accent.GREEN to R.string.accent_green,
        Accent.AMBER to R.string.accent_amber,
        Accent.ROSE to R.string.accent_rose,
        Accent.INK to R.string.accent_ink,
    )
    val shown = Accent.entries.filter { it != Accent.DYNAMIC || Build.VERSION.SDK_INT >= 31 }
    val selected = if (accent == Accent.DYNAMIC && Build.VERSION.SDK_INT < 31) Accent.INDIGO else accent
    FlowRow(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        shown.forEach { a ->
            val color = Color(accentColor(context, dark, a))
            val name = stringResource(names.getValue(a))
            Box(
                Modifier.size(44.dp)
                    .border(2.dp, if (a == selected) MaterialTheme.colorScheme.onSurface else Color.Transparent, CircleShape)
                    .padding(5.dp)
                    .background(color, CircleShape)
                    .selectable(selected = a == selected, onClick = { onAccent(a) }, role = Role.RadioButton)
                    .semanticsLabel(name),
                contentAlignment = Alignment.Center,
            ) {
                if (a == selected) Icon(Icons.Filled.Check, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(18.dp))
            }
        }
    }
    Text(stringResource(names.getValue(selected)), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

private fun Modifier.semanticsLabel(label: String) =
    this.then(Modifier.semantics { contentDescription = label })

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
    Text(
        stringResource(if (unrestricted) R.string.main_battery_unrestricted else R.string.main_battery_restricted),
        style = MaterialTheme.typography.bodyMedium,
    )
    OutlinedButton(onClick = {
        val details = Intent(AndroidSettings.ACTION_APPLICATION_DETAILS_SETTINGS, "package:${context.packageName}".toUri())
        context.startActivity(details)
    }) { Text(stringResource(R.string.main_battery_open)) }
}

/**
 * Run memory_tool in the saved folder: its version, then where its knowledge
 * base is. A wrong folder stops at Set-Location and says so.
 */
private fun testConnection(context: Context): String {
    val settings = Settings(context)
    val target = settings.target() ?: return context.getString(R.string.main_fill_pc)
    val template = settings.command() ?: return KnowledgeBase.problem(settings.basePath) ?: ""
    val key = PhoneKey(context).get()
    fun run(args: List<String>): Pair<Boolean, String> =
        when (val outcome = Ssh.run(target, key, settings.fingerprint, PowerShell.forTransport(template.fill(args)))) {
            is Outcome.NotSent -> false to outcome.reason
            is Outcome.Uncertain -> false to outcome.reason
            is Outcome.Ran -> (outcome.exitStatus == 0) to (outcome.stdout + outcome.stderr).trim().ifEmpty { "exit ${outcome.exitStatus}" }
        }
    val (ok, version) = run(listOf("--version"))
    if (!ok) return version
    val (_, base) = run(listOf("base", "show"))
    val lines = base.lines().map { it.trim() }.filter { it.startsWith("Base folder") || it.startsWith("Initialized") }
    return (listOf(version) + lines.ifEmpty { listOf(base) }).joinToString("\n")
}

private fun copy(context: Context, text: String) {
    context.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("ssh key", text))
}

private fun share(context: Context, text: String) {
    val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text)
    context.startActivity(Intent.createChooser(send, null))
}
