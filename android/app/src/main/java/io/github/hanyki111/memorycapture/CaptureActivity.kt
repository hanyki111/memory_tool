package io.github.hanyki111.memorycapture

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
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
import kotlinx.coroutines.delay
import java.util.Locale

/**
 * The small window that takes one entry: from the app icon, the tile, the
 * widget, or text shared from another app. With [EXTRA_VOICE] it starts with
 * speech input.
 *
 * Sending only keeps the entry and asks for it to be sent; the window closes
 * at once and the result arrives as a short message or a notification.
 */
class CaptureActivity : ComponentActivity() {

    private var text by mutableStateOf("")
    /** Set while a spoken entry is shown before it is sent */
    private var countingDown by mutableStateOf(false)

    private val speech = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val heard = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
        if (result.resultCode == Activity.RESULT_OK && !heard.isNullOrBlank()) {
            text = heard
            countingDown = Settings(this).voiceDelaySeconds > 0
            if (!countingDown) send()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (intent?.action == Intent.ACTION_SEND) {
            text = listOfNotNull(
                intent.getStringExtra(Intent.EXTRA_SUBJECT),
                intent.getStringExtra(Intent.EXTRA_TEXT),
            ).joinToString(" ").trim()
        }
        if (savedInstanceState == null && intent?.getBooleanExtra(EXTRA_VOICE, false) == true) {
            listen()
        }

        setContent {
            AppTheme {
                CaptureWindow(
                    text = text,
                    onText = { text = it; countingDown = false },
                    countingDown = countingDown,
                    delaySeconds = Settings(this).voiceDelaySeconds,
                    onStopCountdown = { countingDown = false },
                    onSend = ::send,
                    onVoice = ::listen,
                    onCancel = ::finish,
                )
            }
        }
    }

    private fun listen() {
        val request = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())
        runCatching { speech.launch(request) }
    }

    private fun send() {
        val entry = text.trim()
        if (entry.isEmpty()) return
        EntryStore.add(this, entry)
        Sender.schedule(this)
        finish()
    }

    companion object {
        const val EXTRA_VOICE = "voice"
    }
}

@Composable
private fun CaptureWindow(
    text: String,
    onText: (String) -> Unit,
    countingDown: Boolean,
    delaySeconds: Int,
    onStopCountdown: () -> Unit,
    onSend: () -> Unit,
    onVoice: () -> Unit,
    onCancel: () -> Unit,
) {
    val focus = remember { FocusRequester() }
    var progress by remember { mutableFloatStateOf(0f) }

    // A spoken entry is shown for a moment, then sent unless the person touches it.
    LaunchedEffect(countingDown) {
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
            if (countingDown) {
                Text(
                    text,
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.fillMaxWidth().clickable { onStopCountdown() },
                )
                LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth())
                Text(stringResource(R.string.capture_tap_to_edit), style = MaterialTheme.typography.bodySmall)
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
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = onVoice) { Text(stringResource(R.string.capture_voice)) }
                Spacer(Modifier.weight(1f))
                TextButton(onClick = onCancel) { Text(stringResource(R.string.cancel)) }
                Button(onClick = onSend, enabled = text.isNotBlank()) { Text(stringResource(R.string.capture_send)) }
            }
        }
    }
}
