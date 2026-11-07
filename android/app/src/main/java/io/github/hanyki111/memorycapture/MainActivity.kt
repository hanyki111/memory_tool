package io.github.hanyki111.memorycapture

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import io.github.hanyki111.memorycapture.data.EntryStore
import io.github.hanyki111.memorycapture.data.Settings
import io.github.hanyki111.memorycapture.ui.AppTheme
import io.github.hanyki111.memorycapture.ui.isAppDark
import io.github.hanyki111.memorycapture.ui.SettingsScreen
import io.github.hanyki111.memorycapture.ui.TimelineModel
import io.github.hanyki111.memorycapture.ui.TimelineScreen

/** The timeline first; the settings behind the gear. */
class MainActivity : ComponentActivity() {

    private val askNotifications = registerForActivityResult(ActivityResultContracts.RequestPermission()) {}

    /** Counts returns to the screen, so what is set elsewhere, like the battery setting, is read again. */
    private val resumed = mutableIntStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Drawn under the system bars on every version, as Android 15 requires;
        // the screens pad for the bars and the keyboard themselves.
        enableEdgeToEdge()
        if (Build.VERSION.SDK_INT >= 33) askNotifications.launch(Manifest.permission.POST_NOTIFICATIONS)
        setContent { App(this, resumed.intValue) }
    }

    override fun onResume() {
        super.onResume()
        resumed.intValue++
    }
}

@Composable
private fun App(activity: ComponentActivity, resumed: Int) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    var fontPercent by remember { mutableIntStateOf(settings.fontPercent) }
    var mode by remember { mutableStateOf(settings.mode) }
    var accent by remember { mutableStateOf(settings.accent) }
    var inSettings by rememberSaveable { mutableStateOf(false) }

    // The status and navigation bar icons follow the app's light or dark, not only the phone's.
    val dark = isAppDark(mode)
    LaunchedEffect(dark) {
        val bars = if (dark) SystemBarStyle.dark(android.graphics.Color.TRANSPARENT)
        else SystemBarStyle.light(android.graphics.Color.TRANSPARENT, android.graphics.Color.TRANSPARENT)
        activity.enableEdgeToEdge(statusBarStyle = bars, navigationBarStyle = bars)
    }

    // The phone's own entries, redrawn whenever they change.
    var version by remember { mutableIntStateOf(0) }
    DisposableEffect(Unit) {
        val listener = { version++ ; Unit }
        EntryStore.listen(listener)
        onDispose { EntryStore.unlisten(listener) }
    }
    val entries = remember(version) { EntryStore.all(context) }

    val scope = rememberCoroutineScope()
    val model = remember { TimelineModel(context.applicationContext, scope) }

    AppTheme(fontPercent, mode, accent) {
        if (inSettings) {
            BackHandler { inSettings = false; model.refresh() }
            SettingsScreen(
                resumed = resumed,
                fontPercent = fontPercent,
                onFontPercent = { fontPercent = it; settings.fontPercent = it },
                mode = mode,
                onMode = { mode = it; settings.mode = it; CaptureWidget.refresh(context) },
                accent = accent,
                onAccent = { accent = it; settings.accent = it; CaptureWidget.refresh(context) },
                onBack = { inSettings = false; model.refresh() },
            )
        } else {
            BackHandler(enabled = model.results != null) { model.clearSearch() }
            TimelineScreen(model, entries, onSettings = { inSettings = true })
        }
    }
}
