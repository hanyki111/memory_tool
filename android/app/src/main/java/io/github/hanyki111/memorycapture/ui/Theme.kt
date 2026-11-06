package io.github.hanyki111.memorycapture.ui

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
import io.github.hanyki111.memorycapture.data.Settings

/**
 * The phone's own colours where it has them (Android 12 and later), light or
 * dark, and the text size chosen in the app on top of the phone's own.
 *
 * @param fontPercent the app's text size; read from the settings when null
 */
@Composable
fun AppTheme(fontPercent: Int? = null, content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val context = LocalContext.current
    val colors = when {
        Build.VERSION.SDK_INT >= 31 && dark -> dynamicDarkColorScheme(context)
        Build.VERSION.SDK_INT >= 31 -> dynamicLightColorScheme(context)
        dark -> darkColorScheme()
        else -> lightColorScheme()
    }
    val percent = fontPercent ?: remember { Settings(context).fontPercent }
    val density = LocalDensity.current
    CompositionLocalProvider(LocalDensity provides Density(density.density, density.fontScale * percent / 100f)) {
        MaterialTheme(colorScheme = colors, content = content)
    }
}
