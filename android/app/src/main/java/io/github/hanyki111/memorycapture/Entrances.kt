package io.github.hanyki111.memorycapture

import android.annotation.SuppressLint
import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.service.quicksettings.TileService
import android.widget.RemoteViews
import io.github.hanyki111.memorycapture.data.EntryStore

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
 * listening. It also shows what is waiting to be sent.
 */
class CaptureWidget : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        ids.forEach { manager.updateAppWidget(it, views(context)) }
    }

    companion object {
        /** Redraw every widget, as after the entries changed. */
        fun refresh(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, CaptureWidget::class.java))
            if (ids.isNotEmpty()) ids.forEach { manager.updateAppWidget(it, views(context)) }
        }

        private fun views(context: Context): RemoteViews {
            val open = PendingIntent.getActivity(
                context, 1, Intent(context, CaptureActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                PendingIntent.FLAG_IMMUTABLE,
            )
            val voice = PendingIntent.getActivity(
                context, 2,
                Intent(context, CaptureActivity::class.java)
                    .putExtra(CaptureActivity.EXTRA_VOICE, true)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                PendingIntent.FLAG_IMMUTABLE,
            )

            val (pending, attention) = EntryStore.counts(context)
            val status = listOfNotNull(
                if (pending > 0) context.getString(R.string.widget_pending, pending) else null,
                if (attention > 0) context.getString(R.string.widget_attention, attention) else null,
            ).joinToString(" · ")

            return RemoteViews(context.packageName, R.layout.widget_capture).apply {
                setOnClickPendingIntent(R.id.widget_field, open)
                setOnClickPendingIntent(R.id.widget_voice, voice)
                setTextViewText(R.id.widget_status, status)
                setViewVisibility(R.id.widget_status, if (status.isEmpty()) android.view.View.GONE else android.view.View.VISIBLE)
            }
        }
    }
}
