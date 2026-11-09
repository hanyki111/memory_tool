package io.github.hanyki111.memorycapture

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import io.github.hanyki111.memorycapture.data.EntryStore
import io.github.hanyki111.memorycapture.data.Settings
import io.github.hanyki111.memorycapture.send.Sender
import io.github.hanyki111.memorycapture.ui.AppTheme
import io.github.hanyki111.memorycapture.ui.TagChips
import io.github.hanyki111.memorycapture.ui.recentTags
import io.github.hanyki111.memorycapture.ui.rememberVoiceInput
import kotlinx.coroutines.delay

/**
 * The small window that takes one entry: from the app icon, the tile, the
 * widget, the icon's shortcuts (which Samsung's routines can run too), or text
 * shared from another app. With [EXTRA_VOICE] or [ACTION_RECORD_VOICE] it
 * starts with speech input.
 *
 * Sending only keeps the entry and asks for it to be sent; the window closes
 * at once and the result arrives as a short message or a notification.
 */
class CaptureActivity : ComponentActivity() {

    private var text by mutableStateOf("")
    /** Set while a spoken entry is shown before it is sent */
    private var countingDown by mutableStateOf(false)

    /** Counts requests to listen, from the intent; the window starts listening on each. */
    private var voiceRequests by mutableIntStateOf(0)

    /** The text came from speech: recent tags are offered */
    private var spoken by mutableStateOf(false)

    /** Restarts the countdown, as after a tag was added */
    private var restart by mutableIntStateOf(0)

    private fun heard(words: String) {
        text = words
        spoken = true
        countingDown = Settings(this).voiceDelaySeconds > 0
        if (!countingDown) send()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (intent?.action == Intent.ACTION_SEND) {
            text = listOfNotNull(
                intent.getStringExtra(Intent.EXTRA_SUBJECT),
                intent.getStringExtra(Intent.EXTRA_TEXT),
            ).joinToString(" ").trim()
        }
        if (savedInstanceState == null && wantsVoice(intent)) voiceRequests++
        val tags = recentTags(this)

        setContent {
            AppTheme {
                val voice = rememberVoiceInput(::heard)
                LaunchedEffect(voiceRequests) { if (voiceRequests > 0) voice.start() }
                CaptureWindow(
                    text = text,
                    onText = { text = it; countingDown = false },
                    countingDown = countingDown,
                    restart = restart,
                    delaySeconds = Settings(this).voiceDelaySeconds,
                    onStopCountdown = { countingDown = false },
                    tags = if (spoken) tags else emptyList(),
                    onTag = { text = it; if (countingDown) restart++ },
                    listening = voice.listening,
                    partial = voice.partial,
                    missed = voice.missed,
                    onSend = ::send,
                    onVoice = voice::start,
                    onCancel = { voice.stop(); finish() },
                )
            }
        }
    }

    /** Asked again while the window is open, as by a routine: listen if asked to. */
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (wantsVoice(intent) && !countingDown) voiceRequests++
    }

    private fun wantsVoice(intent: Intent?) =
        intent?.getBooleanExtra(EXTRA_VOICE, false) == true || intent?.action == ACTION_RECORD_VOICE

    private fun send() {
        val entry = text.trim()
        if (entry.isEmpty()) return
        EntryStore.add(this, entry)
        Sender.schedule(this)
        finish()
    }

    companion object {
        const val EXTRA_VOICE = "voice"
        /** The icon's shortcut that opens the window listening; matches res/xml/shortcuts.xml */
        const val ACTION_RECORD_VOICE = "io.github.hanyki111.memorycapture.RECORD_VOICE"
    }
}

@Composable
private fun CaptureWindow(
    text: String,
    onText: (String) -> Unit,
    countingDown: Boolean,
    restart: Int,
    delaySeconds: Int,
    onStopCountdown: () -> Unit,
    tags: List<String>,
    onTag: (String) -> Unit,
    listening: Boolean,
    partial: String,
    missed: Boolean,
    onSend: () -> Unit,
    onVoice: () -> Unit,
    onCancel: () -> Unit,
) {
    val focus = remember { FocusRequester() }
    var progress by remember { mutableFloatStateOf(0f) }

    // A spoken entry is shown for a moment, then sent unless the person touches it.
    LaunchedEffect(countingDown, restart) {
        if (!countingDown) return@LaunchedEffect
        val steps = delaySeconds * 20
        for (step in 0..steps) {
            progress = step / steps.toFloat()
            delay(50)
        }
        onSend()
    }
    LaunchedEffect(Unit) { if (!countingDown) runCatching { focus.requestFocus() } }

    Surface(shape = androidx.compose.foundation.shape.RoundedCornerShape(24.dp), color = MaterialTheme.colorScheme.surfaceContainer, shadowElevation = 6.dp) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (listening) {
                // In-app speech: what is heard so far.
                Text(
                    partial.ifEmpty { stringResource(R.string.voice_listening) },
                    style = MaterialTheme.typography.bodyLarge,
                    color = if (partial.isEmpty()) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.fillMaxWidth(),
                )
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            } else if (countingDown) {
                Text(
                    text,
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.fillMaxWidth().clickable { onStopCountdown() },
                )
                LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth())
                Text(stringResource(R.string.capture_tap_to_edit), style = MaterialTheme.typography.bodySmall)
                TagChips(tags, text, onTag)
            } else {
                OutlinedTextField(
                    value = text,
                    onValueChange = onText,
                    placeholder = { Text(stringResource(R.string.capture_hint)) },
                    modifier = Modifier.fillMaxWidth().focusRequester(focus),
                    maxLines = 6,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                    keyboardActions = KeyboardActions(onSend = { onSend() }),
                )
                TagChips(tags, text, onText)
                if (missed) Text(stringResource(R.string.voice_missed), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = onVoice) { Text(stringResource(if (listening) R.string.voice_stop else R.string.capture_voice)) }
                Spacer(Modifier.weight(1f))
                TextButton(onClick = onCancel) { Text(stringResource(R.string.cancel)) }
                Button(onClick = onSend, enabled = text.isNotBlank()) { Text(stringResource(R.string.capture_send)) }
            }
        }
    }
}
