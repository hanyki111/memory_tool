package io.github.hanyki111.memorycapture.data

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import io.github.hanyki111.memorycapture.LargeWidget
import io.github.hanyki111.memorycapture.core.Day
import io.github.hanyki111.memorycapture.core.PcArgs
import io.github.hanyki111.memorycapture.core.PcReplies
import io.github.hanyki111.memorycapture.core.Recent
import io.github.hanyki111.memorycapture.core.Recents
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.time.LocalDate
import java.util.concurrent.TimeUnit

/**
 * The PC's latest entries for the large widget: kept only while one is on the
 * home screen, in the app's own files, which backups and transfers leave out
 * (data_extraction_rules.xml). Removing the last large widget deletes them.
 */
object RecentStore {
    private const val FILE = "recent.json"
    private const val PERIODIC = "recent-periodic"
    private const val NOW = "recent-now"

    private fun file(context: Context) = File(context.filesDir, FILE)

    fun load(context: Context): Recent? =
        runCatching { Recents.fromJson(file(context).readText()) }.getOrNull()

    /** Keep the latest entries of these days, when a large widget shows them, and redraw it. */
    fun keep(context: Context, days: List<Day>) {
        if (!LargeWidget.present(context)) return
        val recent = Recent(Recents.latest(days), System.currentTimeMillis())
        runCatching { file(context).writeText(Recents.toJson(recent)) }
        LargeWidget.refresh(context)
    }

    fun clear(context: Context) {
        file(context).delete()
    }

    private val online = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()

    /** Every 30 minutes while a large widget is on the home screen. */
    fun startPeriodic(context: Context) {
        val request = PeriodicWorkRequestBuilder<RecentWorker>(30, TimeUnit.MINUTES).setConstraints(online).build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(PERIODIC, ExistingPeriodicWorkPolicy.KEEP, request)
    }

    fun stop(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(PERIODIC)
        WorkManager.getInstance(context).cancelUniqueWork(NOW)
        clear(context)
    }

    /** Fetch once soon, as after an entry reached the PC. Nothing when no large widget shows it. */
    fun fetchSoon(context: Context) {
        if (!LargeWidget.present(context)) return
        val request = OneTimeWorkRequestBuilder<RecentWorker>().setConstraints(online).build()
        WorkManager.getInstance(context).enqueueUniqueWork(NOW, ExistingWorkPolicy.REPLACE, request)
    }

    /** Ask the PC for the last [Recents.DAYS] days and keep the latest entries. Blocking. */
    fun fetch(context: Context): Boolean {
        if (!LargeWidget.present(context)) return true
        val today = LocalDate.now()
        val from = today.minusDays(Recents.DAYS - 1L).toString()
        return when (val call = Pc.call(context, PcArgs.days(from, today.toString()), PcReplies::days)) {
            is Call.Done -> { keep(context, call.value); true }
            else -> false
        }
    }
}

class RecentWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    // A failure keeps what was fetched before; the widget says when that was.
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        runCatching { RecentStore.fetch(applicationContext) }
        Result.success()
    }
}
