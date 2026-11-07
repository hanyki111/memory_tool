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
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.format.DateFormat
import android.text.style.BackgroundColorSpan
import android.text.style.ForegroundColorSpan
import android.text.style.RelativeSizeSpan
import android.view.View
import android.net.Uri
import android.widget.RemoteViews
import android.widget.RemoteViewsService
import io.github.hanyki111.memorycapture.Widgets.paint
import io.github.hanyki111.memorycapture.core.DayName
import io.github.hanyki111.memorycapture.core.Mode
import io.github.hanyki111.memorycapture.core.Neutrals
import io.github.hanyki111.memorycapture.core.TimelineEntry
import io.github.hanyki111.memorycapture.core.blend
import io.github.hanyki111.memorycapture.core.leadingTags
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
        fun present(context: Context): Boolean = Widgets.ids(context, LargeWidget::class.java).isNotEmpty()

        /** Redraw the widget and its list, as after new entries or a changed setting. */
        fun refresh(context: Context) {
            Widgets.update(context, LargeWidget::class.java) { views(context) }
            val ids = Widgets.ids(context, LargeWidget::class.java)
            @Suppress("DEPRECATION")
            if (ids.isNotEmpty()) AppWidgetManager.getInstance(context).notifyAppWidgetViewDataChanged(ids, R.id.recent_list)
        }

        private fun views(context: Context): RemoteViews {
            val look = Widgets.look(context)
            val recent = RecentStore.load(context)
            val timeline = PendingIntent.getActivity(
                context, 3, Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                PendingIntent.FLAG_IMMUTABLE,
            )
            // A list's rows add nothing to the intent, but Android 12 wants a template it may fill in.
            val rowTemplate = PendingIntent.getActivity(
                context, 4, Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                PendingIntent.FLAG_MUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
            )
            val list = Intent(context, RecentWidgetService::class.java).let { it.setData(Uri.parse(it.toUri(Intent.URI_INTENT_SCHEME))) }
            return Widgets.field(context, R.layout.widget_large).apply {
                paint(R.id.widget_divider, "setBackgroundColor", look) { it.neutrals.line }
                @Suppress("DEPRECATION")
                setRemoteAdapter(R.id.recent_list, list)
                setPendingIntentTemplate(R.id.recent_list, rowTemplate)
                setEmptyView(R.id.recent_list, R.id.recent_empty)
                setTextViewText(
                    R.id.recent_empty,
                    context.getString(if (recent == null) R.string.widget_fetching else R.string.widget_no_entries),
                )
                paint(R.id.recent_empty, "setTextColor", look) { it.neutrals.muted }
                setOnClickPendingIntent(R.id.recent_empty, timeline)
                setTextViewText(
                    R.id.widget_updated,
                    if (recent == null) context.getString(R.string.widget_recent)
                    else context.getString(R.string.widget_header, clock(recent.fetchedAt)),
                )
                paint(R.id.widget_updated, "setTextColor", look) { it.neutrals.muted }
                setOnClickPendingIntent(R.id.widget_updated, timeline)
            }
        }

        /** One row of the list: the time in the accent, then the entry, cut to a line or whole. */
        internal fun row(context: Context, entry: TimelineEntry, look: Widgets.Look, wrap: Boolean): RemoteViews =
            RemoteViews(context.packageName, if (wrap) R.layout.widget_recent_row_wrap else R.layout.widget_recent_row).apply {
                setTextViewText(R.id.recent_when, whenLabel(context, entry))
                setTextViewText(R.id.recent_text, tagged(entry.text, look))
                // The times in the accent, as the app marks the newest entry with it.
                paint(R.id.recent_when, "setTextColor", look) { it.accent }
                paint(R.id.recent_text, "setTextColor", look) { it.neutrals.text }
                setOnClickFillInIntent(R.id.recent_row, Intent())
            }

        /**
         * The entry with its leading `[tags]` as tinted chips, as in the app. A
         * widget's text cannot have round corners, so the chips are square,
         * padded with no-break spaces. Following the phone, the widget swaps its
         * own colours when the phone turns dark, but not a span's, so the chip
         * is a see-through accent that reads on both and keeps the text colour.
         */
        private fun tagged(text: String, look: Widgets.Look): CharSequence {
            val (tags, rest) = leadingTags(text)
            if (tags.isEmpty()) return text
            val side = look.now
            val (tint, ink) = if (look.follows) {
                (side.accent and 0x00FFFFFF or 0x38000000) to null
            } else {
                blend(side.neutrals.background, side.accent, if (look.dark) 0.22 else 0.12) to side.accent
            }
            val out = SpannableStringBuilder()
            tags.forEach { tag ->
                val from = out.length
                out.append("\u00A0").append(tag).append("\u00A0")
                val flags = Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                out.setSpan(BackgroundColorSpan(tint.toInt()), from, out.length, flags)
                out.setSpan(RelativeSizeSpan(0.85f), from, out.length, flags)
                if (ink != null) out.setSpan(ForegroundColorSpan(ink.toInt()), from, out.length, flags)
                out.append(" ")
            }
            return out.append(rest)
        }

        /** "14:30", "어제 14:30" or "11. 5. 14:30". */
        fun whenLabel(context: Context, entry: TimelineEntry): String {
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

/** Gives the large widget's list its rows, from the entries kept on the phone. */
class RecentWidgetService : RemoteViewsService() {
    override fun onGetViewFactory(intent: Intent): RemoteViewsFactory = Rows(applicationContext)

    private class Rows(private val context: Context) : RemoteViewsFactory {
        private var entries: List<TimelineEntry> = emptyList()
        private var look: Widgets.Look? = null
        private var wrap = false

        override fun onCreate() {}
        override fun onDestroy() {}

        override fun onDataSetChanged() {
            val settings = Settings(context)
            entries = RecentStore.load(context)?.entries.orEmpty().take(settings.widgetCount)
            look = Widgets.look(context)
            wrap = settings.widgetWrap
        }

        override fun getCount() = entries.size
        override fun getViewAt(position: Int): RemoteViews? =
            entries.getOrNull(position)?.let { LargeWidget.row(context, it, look ?: Widgets.look(context), wrap) }
        override fun getLoadingView(): RemoteViews? = null
        override fun getViewTypeCount() = 2 // one line, or wrapped
        override fun getItemId(position: Int) = position.toLong()
        override fun hasStableIds() = false
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
