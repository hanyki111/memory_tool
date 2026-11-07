package io.github.hanyki111.memorycapture.ui

import android.content.Context
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
import io.github.hanyki111.memorycapture.core.Accent
import io.github.hanyki111.memorycapture.core.Mode
import io.github.hanyki111.memorycapture.core.Neutrals
import io.github.hanyki111.memorycapture.core.blend
import io.github.hanyki111.memorycapture.data.Settings

/**
 * The app's look: a nearly colourless light or dark screen with one accent,
 * and the text size chosen in the app on top of the phone's own.
 * Anything left null is read from the settings.
 */
@Composable
fun AppTheme(
    fontPercent: Int? = null,
    mode: Mode? = null,
    accent: Accent? = null,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    val dark = (mode ?: remember { settings.mode }).isDark(isSystemInDarkTheme())
    val chosen = accent ?: remember { settings.accent }
    val colors = remember(dark, chosen) { colorScheme(context, dark, chosen) }

    val percent = fontPercent ?: remember { settings.fontPercent }
    val density = LocalDensity.current
    CompositionLocalProvider(LocalDensity provides Density(density.density, density.fontScale * percent / 100f)) {
        MaterialTheme(colorScheme = colors, content = content)
    }
}

/** Whether the app is dark now, for what Compose does not draw (the system bars). */
@Composable
fun isAppDark(mode: Mode): Boolean = mode.isDark(isSystemInDarkTheme())

/** The accent as drawn: the phone's own for [Accent.DYNAMIC] on Android 12 and later. */
fun accentColor(context: Context, dark: Boolean, accent: Accent): Long =
    if (accent == Accent.DYNAMIC && Build.VERSION.SDK_INT >= 31) {
        val scheme = if (dark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        scheme.primary.toArgb().toLong() and 0xFFFFFFFF
    } else {
        accent.color(dark)
    }

private fun colorScheme(context: Context, dark: Boolean, accent: Accent): ColorScheme {
    val n = Neutrals.of(dark)
    val a = accentColor(context, dark, accent)
    fun c(v: Long) = Color(v)
    val tint = c(blend(n.background, a, if (dark) 0.22 else 0.12))
    val base = if (dark) darkColorScheme() else lightColorScheme()
    return base.copy(
        primary = c(a), onPrimary = c(n.onAccent),
        primaryContainer = tint, onPrimaryContainer = c(if (dark) a else blend(a, 0xFF000000, 0.15)),
        secondary = c(a), onSecondary = c(n.onAccent),
        secondaryContainer = tint, onSecondaryContainer = c(n.text),
        tertiary = c(a), onTertiary = c(n.onAccent),
        background = c(n.background), onBackground = c(n.text),
        surface = c(n.background), onSurface = c(n.text),
        surfaceVariant = c(n.raised), onSurfaceVariant = c(n.muted),
        surfaceTint = c(n.background),
        surfaceBright = c(n.raised), surfaceDim = c(n.background),
        surfaceContainerLowest = c(n.background),
        surfaceContainerLow = c(blend(n.background, n.raised, 0.5)),
        surfaceContainer = c(n.raised),
        surfaceContainerHigh = c(n.raised),
        surfaceContainerHighest = c(blend(n.raised, n.line, 0.5)),
        outline = c(n.ring), outlineVariant = c(n.line),
        inverseSurface = c(n.text), inverseOnSurface = c(n.background), inversePrimary = c(accent.color(!dark)),
    )
}
