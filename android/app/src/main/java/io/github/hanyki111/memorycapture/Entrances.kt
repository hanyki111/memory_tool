package io.github.hanyki111.memorycapture

import android.annotation.SuppressLint
import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.os.Build
import android.service.quicksettings.TileService
import android.text.format.DateFormat
import android.view.View
import android.widget.RemoteViews
import io.github.hanyki111.memorycapture.Widgets.paint
import io.github.hanyki111.memorycapture.core.DayName
import io.github.hanyki111.memorycapture.core.Mode
import io.github.hanyki111.memorycapture.core.Neutrals
import io.github.hanyki111.memorycapture.core.Recents
import io.github.hanyki111.memorycapture.core.TimelineEntry
import io.github.hanyki111.memorycapture.core.normalTime
import io.github.hanyki111.memorycapture.data.EntryStore
import io.github.hanyki111.memorycapture.data.RecentStore
import io.github.hanyki111.memorycapture.data.Settings
import io.github.hanyki111.memorycapture.ui.accentColor
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** The quick settings tile: one tap opens the capture window over whatever is on screen. */
class CaptureTile : TileService() {
    @SuppressLint("StartActivityAndCollapseDeprecated")
    override fun onClick() {
        super.onClick()
        val intent = Intent(this, CaptureActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        if (Build.VERSION.SDK_INT >= 34) {
            startActivityAndCollapse(
                PendingIntent.getActivity(this, 0, intent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            )
        } else {
            @Suppress("DEPRECATION")
            startActivityAndCollapse(intent)
        }
    }
}

/**
 * The home screen widget. Android widgets cannot hold a text field, so it
 * looks like one and opens the capture window; the microphone opens it
 * listening. It also shows what is waiting to be sent. Light or dark and the
 * accent follow the app's settings; its text size follows the phone's.
 */
class CaptureWidget : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        ids.forEach { manager.updateAppWidget(it, Widgets.field(context, R.layout.widget_capture)) }
    }

    companion object {
        /** Redraw every widget of the app, as after the entries or the look changed. */
        fun refresh(context: Context) {
            Widgets.update(context, CaptureWidget::class.java) { Widgets.field(context, R.layout.widget_capture) }
            SmallWidget.refresh(context)
            LargeWidget.refresh(context)
        }
    }
}

/** One round button that opens the capture window. */
class SmallWidget : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        ids.forEach { manager.updateAppWidget(it, views(context)) }
    }

    companion object {
        fun refresh(context: Context) = Widgets.update(context, SmallWidget::class.java) { views(context) }

        private fun views(context: Context): RemoteViews {
            val look = Widgets.look(context)
            return RemoteViews(context.packageName, R.layout.widget_small).apply {
                setInt(R.id.widget_root, "setBackgroundResource", look.background(R.drawable.widget_round, R.drawable.widget_round_light, R.drawable.widget_round_dark))
                paint(R.id.widget_icon, "setColorFilter", look) { it.accent }
                setOnClickPendingIntent(R.id.widget_root, Widgets.capture(context, voice = false))
            }
        }
    }
}

/**
 * The field of [CaptureWidget] with the PC's latest entries below it. They are
 * fetched every 30 minutes, when the app loads the timeline, and after an
 * entry reaches the PC, and kept on the phone only while such a widget is on
 * the home screen.
 */
class LargeWidget : AppWidgetProvider() {
    override fun onEnabled(context: Context) {
        RecentStore.startPeriodic(context)
    }

    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        ids.forEach { manager.updateAppWidget(it, views(context)) }
        // Also after a reboot or an update of the app, which may have dropped the work.
        RecentStore.startPeriodic(context)
        if (RecentStore.load(context) == null) RecentStore.fetchSoon(context)
    }

    override fun onDisabled(context: Context) {
        RecentStore.stop(context)
    }

    companion object {
        private val ROWS = listOf(
            Triple(R.id.recent_1, R.id.recent_1_when, R.id.recent_1_text),
            Triple(R.id.recent_2, R.id.recent_2_when, R.id.recent_2_text),
            Triple(R.id.recent_3, R.id.recent_3_when, R.id.recent_3_text),
        )

        fun present(context: Context): Boolean = Widgets.ids(context, LargeWidget::class.java).isNotEmpty()

        fun refresh(context: Context) = Widgets.update(context, LargeWidget::class.java) { views(context) }

        private fun views(context: Context): RemoteViews {
            val look = Widgets.look(context)
            val recent = RecentStore.load(context)
            val entries = recent?.entries.orEmpty().take(Recents.COUNT)
            val timeline = PendingIntent.getActivity(
                context, 3, Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                PendingIntent.FLAG_IMMUTABLE,
            )
            return Widgets.field(context, R.layout.widget_large).apply {
                paint(R.id.widget_divider, "setBackgroundColor", look) { it.neutrals.line }
                ROWS.forEachIndexed { i, (row, whenId, textId) ->
                    val entry = entries.getOrNull(i)
                    setViewVisibility(row, if (entry == null) View.GONE else View.VISIBLE)
                    if (entry != null) {
                        setTextViewText(whenId, whenLabel(context, entry))
                        setTextViewText(textId, entry.text)
                        // The times in the accent, as the app marks the newest entry with it.
                        paint(whenId, "setTextColor", look) { it.accent }
                        paint(textId, "setTextColor", look) { it.neutrals.text }
                    }
                    setOnClickPendingIntent(row, timeline)
                }
                val note = when {
                    recent == null -> context.getString(R.string.widget_fetching)
                    entries.isEmpty() -> context.getString(R.string.widget_no_entries)
                    else -> context.getString(R.string.widget_updated, clock(recent.fetchedAt))
                }
                setTextViewText(R.id.widget_updated, note)
                paint(R.id.widget_updated, "setTextColor", look) { it.neutrals.muted }
                setOnClickPendingIntent(R.id.widget_updated, timeline)
            }
        }

        /** "14:30", "어제 14:30" or "11. 5. 14:30". */
        private fun whenLabel(context: Context, entry: TimelineEntry): String {
            val time = normalTime(entry.time)
            return when (val day = DayName.of(entry.date, LocalDate.now())) {
                DayName.Today, null -> time
                DayName.Yesterday -> "${context.getString(R.string.widget_yesterday)} $time"
                is DayName.Other -> {
                    val pattern = DateFormat.getBestDateTimePattern(Locale.getDefault(), "Md")
                    "${day.day.format(DateTimeFormatter.ofPattern(pattern, Locale.getDefault()))} $time"
                }
            }
        }

        private fun clock(millis: Long): String {
            val at = Instant.ofEpochMilli(millis).atZone(ZoneId.systemDefault())
            val pattern = if (at.toLocalDate() == LocalDate.now()) "HH:mm" else "M/d HH:mm"
            return at.format(DateTimeFormatter.ofPattern(pattern))
        }
    }
}

/** What the widgets share: their look, the field, and opening the capture window. */
internal object Widgets {
    /** The colours of one side, light or dark. */
    class Side(val neutrals: Neutrals, val accent: Long)

    /**
     * The app's look for a widget. Set to follow the phone, the widget carries
     * both sides and the launcher picks one each time it draws (Android 12 and
     * later), so it turns dark with the phone even while the app is closed.
     */
    class Look(val follows: Boolean, val dark: Boolean, val light: Side, val darkSide: Side) {
        val now get() = if (dark) darkSide else light

        fun background(follow: Int, light: Int, dark: Int) = when {
            follows -> follow
            this.dark -> dark
            else -> light
        }
    }

    fun look(context: Context): Look {
        val settings = Settings(context)
        val systemDark = (context.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
        return Look(
            follows = settings.mode == Mode.SYSTEM && Build.VERSION.SDK_INT >= 31,
            dark = settings.mode.isDark(systemDark),
            light = Side(Neutrals.LIGHT, accentColor(context, false, settings.accent)),
            darkSide = Side(Neutrals.DARK, accentColor(context, true, settings.accent)),
        )
    }

    /** Call [method] with [pick]'s colour: both sides when the look follows the phone, else the current one. */
    fun RemoteViews.paint(id: Int, method: String, look: Look, pick: (Side) -> Long) {
        if (look.follows && Build.VERSION.SDK_INT >= 31) {
            setColorInt(id, method, pick(look.light).toInt(), pick(look.darkSide).toInt())
        } else {
            setInt(id, method, pick(look.now).toInt())
        }
    }

    fun ids(context: Context, provider: Class<*>): IntArray =
        AppWidgetManager.getInstance(context).getAppWidgetIds(ComponentName(context, provider))

    fun update(context: Context, provider: Class<*>, views: () -> RemoteViews) {
        val ids = ids(context, provider)
        if (ids.isEmpty()) return
        val manager = AppWidgetManager.getInstance(context)
        ids.forEach { manager.updateAppWidget(it, views()) }
    }

    fun capture(context: Context, voice: Boolean): PendingIntent = PendingIntent.getActivity(
        context, if (voice) 2 else 1,
        Intent(context, CaptureActivity::class.java)
            .putExtra(CaptureActivity.EXTRA_VOICE, voice)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
        PendingIntent.FLAG_IMMUTABLE,
    )

    /** The field-like row with the microphone and what is waiting; [layout] holds it. */
    fun field(context: Context, layout: Int): RemoteViews {
        val look = look(context)
        val (pending, attention) = EntryStore.counts(context)
        val status = listOfNotNull(
            if (pending > 0) context.getString(R.string.widget_pending, pending) else null,
            if (attention > 0) context.getString(R.string.widget_attention, attention) else null,
        ).joinToString(" · ")
        return RemoteViews(context.packageName, layout).apply {
            setInt(R.id.widget_root, "setBackgroundResource", look.background(R.drawable.widget_background, R.drawable.widget_background_light, R.drawable.widget_background_dark))
            paint(R.id.widget_hint, "setTextColor", look) { it.neutrals.muted }
            paint(R.id.widget_status, "setTextColor", look) { side ->
                if (attention == 0) side.accent else if (side === look.darkSide) 0xFFF2B8B5 else 0xFFB3261E
            }
            paint(R.id.widget_voice, "setColorFilter", look) { it.accent }
            setOnClickPendingIntent(R.id.widget_field, capture(context, voice = false))
            setOnClickPendingIntent(R.id.widget_voice, capture(context, voice = true))
            setTextViewText(R.id.widget_status, status)
            setViewVisibility(R.id.widget_status, if (status.isEmpty()) View.GONE else View.VISIBLE)
        }
    }
}
