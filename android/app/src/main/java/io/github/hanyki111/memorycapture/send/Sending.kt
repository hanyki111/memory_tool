package io.github.hanyki111.memorycapture.send

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.ForegroundInfo
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OutOfQuotaPolicy
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import io.github.hanyki111.memorycapture.MainActivity
import io.github.hanyki111.memorycapture.R
import io.github.hanyki111.memorycapture.core.CommandTemplate
import io.github.hanyki111.memorycapture.core.Outcome
import io.github.hanyki111.memorycapture.core.PowerShell
import io.github.hanyki111.memorycapture.core.RecordReply
import io.github.hanyki111.memorycapture.core.Retry
import io.github.hanyki111.memorycapture.core.State
import io.github.hanyki111.memorycapture.core.Transitions
import io.github.hanyki111.memorycapture.core.dayArgs
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

    /** One send at a time, so a send started while another runs cannot send the same entry twice. */
    private val sending = Any()

    private val network = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()

    /**
     * Send as soon as there is a network; returns at once. Expedited work is
     * run promptly even when the app is in the background, where ordinary
     * work may be held back to save battery.
     */
    fun schedule(context: Context) {
        val request = OneTimeWorkRequestBuilder<SendWorker>()
            .setConstraints(network)
            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(WORK, ExistingWorkPolicy.REPLACE, request)
    }

    /** Try again after a while, when the PC could not be reached. Called from the running worker. */
    fun retryLater(context: Context, seconds: Long) {
        val request = OneTimeWorkRequestBuilder<SendWorker>()
            .setConstraints(network)
            .setInitialDelay(seconds, TimeUnit.SECONDS)
            .build()
        // Runs after the current worker ends; a new entry or a returning network replaces it.
        WorkManager.getInstance(context).enqueueUniqueWork(WORK, ExistingWorkPolicy.APPEND_OR_REPLACE, request)
    }

    /**
     * Send what is waiting.
     *
     * @return true when something is still waiting for the network, so the
     *     worker should try again later.
     */
    fun sendAll(context: Context): Boolean = synchronized(sending) { sendWaiting(context) }

    private fun sendWaiting(context: Context): Boolean {
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

        fun run(args: List<String>) = runPatiently { Ssh.run(target, key, settings.fingerprint, PowerShell.forTransport(template.fill(args))) }

        while (true) {
            val entry = Transitions.next(EntryStore.all(context)) ?: return false

            if (entry.state == State.CHECK) {
                // It may be on the PC already: look before sending it again.
                val outcome = run(dayArgs(entry.date))
                val next = Transitions.applyCheck(entry, outcome, System.currentTimeMillis())
                EntryStore.put(context, next)
                when {
                    outcome is Outcome.NotSent && outcome.needsPerson -> {
                        Notifier.attention(context, outcome.reason)
                        return false
                    }
                    outcome !is Outcome.Ran -> return true
                    next.state == State.SENT -> Notifier.toast(context, context.getString(R.string.toast_already_recorded, entry.time))
                    next.state == State.ATTENTION ->
                        Notifier.attention(context, context.getString(R.string.notify_check_failed, entry.text.take(40)))
                }
                // Not on the PC: the loop sends it next.
                continue
            }

            val outcome = run(recordArgs(entry.text, entry.date, entry.time))
            val (next, reply) = Transitions.applyOutcome(entry, outcome, System.currentTimeMillis())
            EntryStore.put(context, next)

            when {
                outcome is Outcome.NotSent && outcome.needsPerson -> {
                    Notifier.attention(context, outcome.reason)
                    return false
                }
                outcome is Outcome.NotSent -> return true
                // Uncertain: the entry is now checked, which the loop does next.
                outcome is Outcome.Uncertain -> Unit
                reply is RecordReply.Recorded -> {
                    Notifier.toast(context, context.getString(R.string.toast_recorded, reply.time ?: entry.time))
                    reply.notices.forEach { Notifier.notice(context, it) }
                }
                reply is RecordReply.Refused -> Notifier.attention(context, reply.message.ifEmpty { reply.code })
                reply is RecordReply.Unreadable && next.state == State.ATTENTION ->
                    Notifier.attention(context, reply.firstLine.ifEmpty { context.getString(R.string.notify_unreadable) })
            }
        }
    }

    /** Try again a few times, shortly, while the PC certainly was not reached. */
    private fun runPatiently(send: () -> Outcome): Outcome {
        var outcome = send()
        for (wait in Retry.QUICK_WAITS) {
            if (outcome !is Outcome.NotSent || outcome.needsPerson) return outcome
            Thread.sleep(wait * 1000)
            outcome = send()
        }
        return outcome
    }
}

class SendWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val context = applicationContext
        val again = runCatching { Sender.sendAll(context) }.getOrElse { error ->
            Notifier.attention(context, error.message ?: error.javaClass.simpleName)
            false
        }
        if (again) {
            val attempts = Transitions.next(EntryStore.all(context))?.attempts ?: 1
            Sender.retryLater(context, Retry.delaySeconds(attempts))
        }
        NetworkWatch.update(context)
        Result.success()
    }

    /** Android 11 and older run expedited work as a foreground service, which shows this. */
    override suspend fun getForegroundInfo(): ForegroundInfo = ForegroundInfo(Notifier.SENDING_ID, Notifier.sending(applicationContext))
}

/**
 * Wakes the app when a working network appears, while entries are waiting.
 *
 * Android delivers the PendingIntent even when the app is not running, so an
 * entry written without a connection is sent as soon as the connection is
 * back. Only validated networks count: right after airplane mode is turned
 * off, the network may be up before it can reach anything.
 */
object NetworkWatch {
    private fun intent(context: Context): PendingIntent = PendingIntent.getBroadcast(
        context, 0, Intent(context, NetworkReceiver::class.java),
        // Android adds the network to the intent, so it must be mutable; the intent is explicit.
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE,
    )

    /** Whether this process has registered; null until it has decided once. */
    private var watching: Boolean? = null

    /**
     * Watch while something is waiting, and stop once nothing is. Registering
     * wakes the app at once when a network is already there, so it is done only
     * when the answer changes, not on every change to the entries.
     */
    @Synchronized
    fun update(context: Context) {
        val manager = context.getSystemService(ConnectivityManager::class.java) ?: return
        val waiting = Transitions.next(EntryStore.all(context)) != null
        if (watching == waiting) return
        watching = waiting
        runCatching {
            if (waiting) {
                val request = NetworkRequest.Builder()
                    .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                    .addCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
                    .build()
                // Registering the same PendingIntent again replaces the earlier registration.
                manager.registerNetworkCallback(request, intent(context))
            } else {
                manager.unregisterNetworkCallback(intent(context))
            }
        }
    }
}

class NetworkReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (Transitions.next(EntryStore.all(context)) != null) Sender.schedule(context)
    }
}

/** Short confirmations, and notifications for what needs the person. */
object Notifier {
    private const val CHANNEL_NOTICES = "notices"
    private const val CHANNEL_ATTENTION = "attention"
    private const val CHANNEL_SENDING = "sending"
    const val SENDING_ID = 1
    private var nextId = 1000

    /** The quiet notification shown while sending, where Android requires one. */
    fun sending(context: Context): Notification {
        channels(context)
        return NotificationCompat.Builder(context, CHANNEL_SENDING)
            .setSmallIcon(R.drawable.ic_capture)
            .setContentTitle(context.getString(R.string.notify_sending))
            .setSilent(true)
            .build()
    }

    fun channels(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_SENDING, context.getString(R.string.channel_sending), NotificationManager.IMPORTANCE_MIN)
        )
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
