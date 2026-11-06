package io.github.hanyki111.memorycapture.send

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import io.github.hanyki111.memorycapture.MainActivity
import io.github.hanyki111.memorycapture.R
import io.github.hanyki111.memorycapture.core.CommandTemplate
import io.github.hanyki111.memorycapture.core.Outcome
import io.github.hanyki111.memorycapture.core.PowerShell
import io.github.hanyki111.memorycapture.core.RecordReply
import io.github.hanyki111.memorycapture.core.Transitions
import io.github.hanyki111.memorycapture.core.recordArgs
import io.github.hanyki111.memorycapture.data.EntryStore
import io.github.hanyki111.memorycapture.data.PhoneKey
import io.github.hanyki111.memorycapture.data.Settings
import io.github.hanyki111.memorycapture.ssh.Ssh
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

/** Sends the waiting entries, oldest first, until one cannot be sent. */
object Sender {
    private const val WORK = "send"

    /** Ask Android to send when there is a network; returns at once. */
    fun schedule(context: Context) {
        val request = OneTimeWorkRequestBuilder<SendWorker>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(WORK, ExistingWorkPolicy.REPLACE, request)
    }

    /**
     * Send what is waiting.
     *
     * @return true when something is still waiting for the network, so the
     *     worker should try again later.
     */
    fun sendAll(context: Context): Boolean {
        val settings = Settings(context)
        val missing = settings.missing()
        if (missing != null) {
            if (Transitions.next(EntryStore.all(context)) != null) {
                Notifier.attention(context, context.getString(R.string.notify_setup_needed, missing))
            }
            return false
        }

        val target = settings.target()!!
        val template = CommandTemplate.parse(settings.template).getOrThrow()
        val key = PhoneKey(context).get()

        while (true) {
            val entry = Transitions.next(EntryStore.all(context)) ?: return false
            val command = PowerShell.forTransport(template.fill(recordArgs(entry.text, entry.date, entry.time)))
            val outcome = Ssh.run(target, key, settings.fingerprint, command)
            val (next, reply) = Transitions.applyOutcome(entry, outcome, System.currentTimeMillis())
            EntryStore.put(context, next)

            when {
                outcome is Outcome.NotSent && outcome.needsPerson -> {
                    Notifier.attention(context, outcome.reason)
                    return false
                }
                outcome is Outcome.NotSent -> return true
                outcome is Outcome.Uncertain -> Notifier.attention(context, context.getString(R.string.notify_uncertain, entry.text.take(40)))
                reply is RecordReply.Recorded -> {
                    Notifier.toast(context, context.getString(R.string.toast_recorded, reply.time ?: entry.time))
                    reply.notices.forEach { Notifier.notice(context, it) }
                }
                reply is RecordReply.Refused -> Notifier.attention(context, reply.message.ifEmpty { reply.code })
                reply is RecordReply.Unreadable -> Notifier.attention(context, reply.firstLine.ifEmpty { context.getString(R.string.notify_unreadable) })
            }
        }
    }
}

class SendWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val again = runCatching { Sender.sendAll(applicationContext) }.getOrElse { error ->
            Notifier.attention(applicationContext, error.message ?: error.javaClass.simpleName)
            false
        }
        if (again) Result.retry() else Result.success()
    }
}

/** Short confirmations, and notifications for what needs the person. */
object Notifier {
    private const val CHANNEL_NOTICES = "notices"
    private const val CHANNEL_ATTENTION = "attention"
    private var nextId = 1000

    fun channels(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_NOTICES, context.getString(R.string.channel_notices), NotificationManager.IMPORTANCE_DEFAULT)
        )
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ATTENTION, context.getString(R.string.channel_attention), NotificationManager.IMPORTANCE_HIGH)
        )
    }

    fun toast(context: Context, text: String) {
        Handler(Looper.getMainLooper()).post { Toast.makeText(context.applicationContext, text, Toast.LENGTH_SHORT).show() }
    }

    fun notice(context: Context, text: String) = notify(context, CHANNEL_NOTICES, text)

    fun attention(context: Context, text: String) = notify(context, CHANNEL_ATTENTION, text)

    private fun notify(context: Context, channel: String, text: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            toast(context, text)
            return
        }
        channels(context)
        val open = PendingIntent.getActivity(
            context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(context, channel)
            .setSmallIcon(R.drawable.ic_capture)
            .setContentTitle(context.getString(R.string.app_name))
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setContentIntent(open)
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(context).notify(nextId++, notification)
    }
}
