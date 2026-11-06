package io.github.hanyki111.memorycapture.core

import org.json.JSONArray
import org.json.JSONObject

/**
 * Entries waiting to be sent, and those recently sent.
 *
 * Every entry is kept until it is sent, so nothing written on the phone is
 * lost while the PC cannot be reached. An entry is sent again on its own only
 * when the command certainly did not run; otherwise it needs the person.
 */
enum class State {
    /** Waiting to be sent, or to be sent again */
    PENDING,

    /** Recorded on the PC */
    SENT,

    /** Needs the person: it may have been recorded, or memory_tool refused it */
    ATTENTION,
}

data class Entry(
    val id: String,
    val text: String,
    /** When it was written, as memory_tool takes it: YYYY-MM-DD and HH:MM */
    val date: String,
    val time: String,
    val state: State = State.PENDING,
    val attempts: Int = 0,
    /** Why it is waiting or needs attention, for the person */
    val note: String = "",
    /** Set when the command may have run, so sending again could record it twice */
    val maybeRecorded: Boolean = false,
    /** When the state last changed, in milliseconds */
    val changedAt: Long = 0,
)

/** What happened when an entry was sent. */
sealed class Outcome {
    /** The command never ran: no connection, refused, wrong key, wrong PC. Safe to send again. */
    data class NotSent(val reason: String) : Outcome()

    /** The connection broke after the command was sent; it may or may not have run. */
    data class Uncertain(val reason: String) : Outcome()

    /** The command ran and this is what it printed. */
    data class Ran(val stdout: String, val stderr: String, val exitStatus: Int) : Outcome()
}

/** How an entry's state changes. Pure functions over immutable entries. */
object Transitions {
    /** At most this many sent entries are kept for the "recently sent" list. */
    const val KEEP_SENT = 50

    fun applyOutcome(entry: Entry, outcome: Outcome, now: Long): Pair<Entry, RecordReply?> {
        val tried = entry.copy(attempts = entry.attempts + 1, changedAt = now)
        return when (outcome) {
            is Outcome.NotSent -> tried.copy(state = State.PENDING, note = outcome.reason, maybeRecorded = false) to null
            is Outcome.Uncertain -> tried.copy(state = State.ATTENTION, note = outcome.reason, maybeRecorded = true) to null
            is Outcome.Ran -> {
                val reply = Replies.parse(outcome.stdout, outcome.stderr, outcome.exitStatus)
                val next = when (reply) {
                    is RecordReply.Recorded -> tried.copy(state = State.SENT, note = "", maybeRecorded = false)
                    is RecordReply.Refused -> tried.copy(state = State.ATTENTION, note = reply.message.ifEmpty { reply.code }, maybeRecorded = false)
                    is RecordReply.Unreadable -> tried.copy(state = State.ATTENTION, note = reply.firstLine, maybeRecorded = reply.exitStatus == 0)
                }
                next to reply
            }
        }
    }

    /** The person checked the PC and found the entry recorded. */
    fun markSent(entry: Entry, now: Long): Entry = entry.copy(state = State.SENT, note = "", maybeRecorded = false, changedAt = now)

    /** The person asked to send it again. */
    fun resend(entry: Entry, now: Long): Entry = entry.copy(state = State.PENDING, note = "", maybeRecorded = false, changedAt = now)

    /** Keep every unsent entry and only the latest sent ones. */
    fun trim(entries: List<Entry>): List<Entry> {
        val sent = entries.filter { it.state == State.SENT }.sortedByDescending { it.changedAt }.take(KEEP_SENT).toSet()
        return entries.filter { it.state != State.SENT || it in sent }
    }

    /** The next entry to send: the oldest waiting one, so entries keep their order. */
    fun next(entries: List<Entry>): Entry? =
        entries.filter { it.state == State.PENDING }.minWithOrNull(compareBy({ it.date }, { it.time }, { it.id }))
}

/** The stored form of the entries. */
object EntryJson {
    fun write(entries: List<Entry>): String {
        val array = JSONArray()
        for (e in entries) {
            array.put(
                JSONObject()
                    .put("id", e.id)
                    .put("text", e.text)
                    .put("date", e.date)
                    .put("time", e.time)
                    .put("state", e.state.name)
                    .put("attempts", e.attempts)
                    .put("note", e.note)
                    .put("maybeRecorded", e.maybeRecorded)
                    .put("changedAt", e.changedAt)
            )
        }
        return array.toString()
    }

    fun read(text: String): List<Entry> {
        if (text.isBlank()) return emptyList()
        val array = JSONArray(text)
        return (0 until array.length()).map { i ->
            val o = array.getJSONObject(i)
            Entry(
                id = o.getString("id"),
                text = o.getString("text"),
                date = o.getString("date"),
                time = o.getString("time"),
                state = runCatching { State.valueOf(o.getString("state")) }.getOrDefault(State.PENDING),
                attempts = o.optInt("attempts", 0),
                note = o.optString("note", ""),
                maybeRecorded = o.optBoolean("maybeRecorded", false),
                changedAt = o.optLong("changedAt", 0),
            )
        }
    }
}
