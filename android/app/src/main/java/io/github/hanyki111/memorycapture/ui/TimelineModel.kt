package io.github.hanyki111.memorycapture.ui

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import io.github.hanyki111.memorycapture.R
import io.github.hanyki111.memorycapture.core.Day
import io.github.hanyki111.memorycapture.core.Days
import io.github.hanyki111.memorycapture.core.PcArgs
import io.github.hanyki111.memorycapture.core.PcReplies
import io.github.hanyki111.memorycapture.core.TimelineEntry
import io.github.hanyki111.memorycapture.core.newestFirst
import io.github.hanyki111.memorycapture.data.Call
import io.github.hanyki111.memorycapture.data.Pc
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.LocalDate

/**
 * The PC's timeline as the app has loaded it, and the search.
 *
 * Every read and change runs memory_tool on the PC; nothing of the timeline
 * is stored on the phone.
 */
class TimelineModel(private val context: Context, private val scope: CoroutineScope) {
    /** Loaded days, newest first; only days with entries */
    var days by mutableStateOf<List<Day>>(emptyList())
        private set

    /** The first day loaded so far; everything from it to today is loaded */
    var oldest by mutableStateOf<LocalDate?>(null)
        private set

    var loading by mutableStateOf(false)
        private set
    var refreshing by mutableStateOf(false)
        private set
    var error by mutableStateOf<String?>(null)
        private set

    /**
     * Whether reaching the end loads the next week by itself. It does only
     * after a week that had entries, so an empty stretch is never walked
     * through on its own; the person asks for more with a button.
     */
    var autoLoad by mutableStateOf(true)
        private set

    var query by mutableStateOf("")
    /** Search results, newest first; null when not searching */
    var results by mutableStateOf<List<TimelineEntry>?>(null)
        private set
    var searching by mutableStateOf(false)
        private set
    var searchError by mutableStateOf<String?>(null)
        private set

    /** A short message for the snackbar */
    var message by mutableStateOf<String?>(null)

    private var job: Job? = null

    private suspend fun <T> pc(args: List<String>, read: (String, String) -> io.github.hanyki111.memorycapture.core.PcReply<T>): Call<T> =
        withContext(Dispatchers.IO) { Pc.call(context, args, read) }

    private fun failure(call: Call<*>): String? = when (call) {
        is Call.Done -> null
        is Call.Refused -> call.message
        is Call.Failed -> call.reason
    }

    /** The first week, once. */
    fun start() {
        if (oldest == null && !loading) loadOlder()
    }

    /** The week before what is loaded. */
    fun loadOlder() {
        if (loading) return
        val to = oldest?.minusDays(1) ?: LocalDate.now()
        val from = to.minusDays(PAGE_DAYS - 1)
        loading = true
        error = null
        job = scope.launch {
            val call = pc(PcArgs.days(from.toString(), to.toString()), PcReplies::days)
            loading = false
            if (call is Call.Done) {
                days = Days.merge(days, from.toString(), to.toString(), call.value)
                oldest = from
                autoLoad = call.value.any { it.entries.isNotEmpty() }
            } else {
                error = failure(call)
            }
        }
    }

    /** Everything loaded so far, again. */
    fun refresh() {
        val from = oldest ?: return start()
        if (refreshing) return
        refreshing = true
        scope.launch {
            val to = LocalDate.now()
            val call = pc(PcArgs.days(from.toString(), to.toString()), PcReplies::days)
            refreshing = false
            if (call is Call.Done) {
                days = Days.merge(days, from.toString(), to.toString(), call.value)
                error = null
            } else {
                message = failure(call)
            }
            if (results != null) search()
        }
    }

    /** Some days again, after a change or a sent entry; days outside what is loaded are left alone. */
    fun reload(dates: Collection<String>) {
        val from = oldest ?: return
        val wanted = dates.filter { it >= from.toString() }.distinct()
        if (wanted.isEmpty()) return
        scope.launch {
            for (date in wanted) {
                val call = pc(PcArgs.days(date, date), PcReplies::days)
                if (call is Call.Done) days = Days.merge(days, date, date, call.value)
            }
        }
    }

    fun search() {
        val q = query.trim()
        if (q.isEmpty()) return clearSearch()
        searching = true
        searchError = null
        scope.launch {
            val call = pc(PcArgs.search(q), PcReplies::search)
            searching = false
            if (call is Call.Done) results = newestFirst(call.value) else searchError = failure(call)
        }
    }

    fun clearSearch() {
        query = ""
        results = null
        searchError = null
        searching = false
    }

    /**
     * Change an entry. [done] gets null when the sheet can close, or a reason
     * to show in it.
     */
    fun save(entry: TimelineEntry, date: String, time: String, text: String, done: (String?) -> Unit) =
        change(entry, PcArgs.edit(entry, date, time, text), R.string.edit_saved, done)

    fun delete(entry: TimelineEntry, done: (String?) -> Unit) =
        change(entry, PcArgs.delete(entry), R.string.edit_deleted, done)

    private fun change(entry: TimelineEntry, args: List<String>, ok: Int, done: (String?) -> Unit) {
        scope.launch {
            when (val call = pc(args, PcReplies::changed)) {
                is Call.Done -> {
                    done(null)
                    message = context.getString(ok)
                    afterChange(listOf(entry.date, call.value.first.date))
                }
                is Call.Refused ->
                    if (call.code == NOT_FOUND) {
                        done(null)
                        message = context.getString(R.string.edit_changed_on_pc)
                        afterChange(listOf(entry.date))
                    } else {
                        done(call.message)
                    }
                is Call.Failed ->
                    if (call.mayHaveRun) {
                        done(null)
                        message = context.getString(R.string.edit_unknown)
                        afterChange(listOf(entry.date))
                    } else {
                        done(call.reason)
                    }
            }
        }
    }

    private fun afterChange(dates: List<String>) {
        reload(dates)
        if (results != null) search()
    }

    private companion object {
        const val PAGE_DAYS = 7L
        const val NOT_FOUND = "not_found"
    }
}
