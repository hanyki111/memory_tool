package io.github.hanyki111.memorycapture.ui

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import io.github.hanyki111.memorycapture.core.Tags
import io.github.hanyki111.memorycapture.data.EntryStore
import io.github.hanyki111.memorycapture.data.RecentStore
import io.github.hanyki111.memorycapture.data.Settings
import java.util.Locale

/**
 * Speech input, the way the settings choose: Google's speech window, or
 * recognition inside the app through the phone's default speech service
 * (Samsung's, where the phone offers it and it is chosen), which shows what
 * it hears and needs the microphone permission. In-app recognition falls back
 * to the window when the phone has no service or it fails.
 */
class VoiceInput internal constructor() {
    /** Listening inside the app */
    var listening by mutableStateOf(false)
        internal set

    /** What has been heard so far, while listening inside the app */
    var partial by mutableStateOf("")
        internal set

    /** Nothing was heard, after listening inside the app */
    var missed by mutableStateOf(false)
        internal set

    internal var startNow: () -> Unit = {}
    internal var stopNow: () -> Unit = {}

    fun start() = startNow()
    fun stop() = stopNow()
}

@Composable
fun rememberVoiceInput(onHeard: (String) -> Unit): VoiceInput {
    val context = LocalContext.current
    val heard by rememberUpdatedState(onHeard)
    val voice = remember { VoiceInput() }

    val window = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val text = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
        if (result.resultCode == Activity.RESULT_OK && !text.isNullOrBlank()) heard(text)
    }
    fun openWindow() {
        runCatching { window.launch(speechIntent()) }
    }

    val recognizer = remember {
        if (SpeechRecognizer.isRecognitionAvailable(context)) SpeechRecognizer.createSpeechRecognizer(context) else null
    }
    DisposableEffect(recognizer) {
        recognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onEvent(eventType: Int, params: Bundle?) {}

            override fun onPartialResults(partialResults: Bundle?) {
                first(partialResults)?.let { voice.partial = it }
            }

            override fun onResults(results: Bundle?) {
                voice.listening = false
                val text = first(results)
                if (text.isNullOrBlank()) voice.missed = true else heard(text)
                voice.partial = ""
            }

            override fun onError(error: Int) {
                voice.listening = false
                voice.partial = ""
                when (error) {
                    // Nothing said, or not understood: say so, and let the person try again.
                    SpeechRecognizer.ERROR_NO_MATCH, SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> voice.missed = true
                    // The service is busy or was stopped on purpose.
                    SpeechRecognizer.ERROR_RECOGNIZER_BUSY, SpeechRecognizer.ERROR_CLIENT -> Unit
                    // Anything else (no network, no service, no permission): the window still works.
                    else -> openWindow()
                }
            }
        })
        onDispose { recognizer?.destroy() }
    }

    fun listenHere() {
        val r = recognizer ?: return openWindow()
        voice.missed = false
        voice.partial = ""
        voice.listening = true
        runCatching {
            r.startListening(speechIntent().putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true))
        }.onFailure {
            voice.listening = false
            openWindow()
        }
    }

    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) listenHere() else openWindow()
    }

    voice.startNow = {
        when {
            voice.listening -> recognizer?.stopListening()
            !Settings(context).voiceInApp || recognizer == null -> openWindow()
            hasMicrophone(context) -> listenHere()
            else -> permission.launch(Manifest.permission.RECORD_AUDIO)
        }
    }
    voice.stopNow = {
        if (voice.listening) {
            recognizer?.cancel()
            voice.listening = false
            voice.partial = ""
        }
    }
    return voice
}

private fun speechIntent() = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
    .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
    .putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())

private fun first(results: Bundle?): String? =
    results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()

private fun hasMicrophone(context: Context) =
    ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

/**
 * Tags used lately, newest first: from the phone's own entries, the large
 * widget's entries, and [more] (the timeline the app has loaded).
 */
fun recentTags(context: Context, more: List<String> = emptyList()): List<String> {
    val phone = EntryStore.all(context).sortedWith(compareByDescending<io.github.hanyki111.memorycapture.core.Entry> { it.date }.thenByDescending { it.time })
        .map { it.text }
    val widget = RecentStore.load(context)?.entries.orEmpty().map { it.text }
    return Tags.recent(phone + more + widget)
}

/** Recent tags as chips; a chip puts its tag before the text or takes it away. */
@Composable
fun TagChips(tags: List<String>, text: String, onText: (String) -> Unit, modifier: Modifier = Modifier) {
    if (tags.isEmpty()) return
    Row(modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        tags.forEach { tag ->
            FilterChip(
                selected = Tags.has(text, tag),
                onClick = { onText(Tags.toggle(text, tag)) },
                label = { Text(tag) },
            )
        }
    }
}
