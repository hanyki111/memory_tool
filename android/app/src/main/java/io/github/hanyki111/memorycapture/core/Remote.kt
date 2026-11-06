package io.github.hanyki111.memorycapture.core

import org.json.JSONArray
import org.json.JSONObject

/** One entry of the PC's timeline, as memory_tool's JSON gives it. */
data class TimelineEntry(val date: String, val time: String, val text: String, val tags: List<String> = emptyList())

/** One day of the PC's timeline. */
data class Day(val date: String, val entries: List<TimelineEntry>)

/** What memory_tool answered to a read or a change. */
sealed class PcReply<out T> {
    data class Ok<T>(val value: T) : PcReply<T>()

    /** memory_tool refused, with its failure code, such as `not_found` or `future_time`. */
    data class Refused(val code: String, val message: String) : PcReply<Nothing>()

    /** Not memory_tool's JSON: an old memory_tool without the command, a wrong command, and so on. */
    data class Unreadable(val firstLine: String) : PcReply<Nothing>()
}

/**
 * memory_tool's arguments for reading and changing the timeline.
 *
 * Values that a person wrote go after `=` in one argument, so text starting
 * with `-` is never read as an option.
 */
object PcArgs {
    fun days(from: String, to: String) = listOf("days", "--json", "--from", from, "--to", to)

    // No cache: an entry just edited must show as it now is.
    fun search(query: String) = listOf("search", "--json", "--no-cache", "--type", "timeline", "--", oneLine(query))

    fun find(date: String, time: String, text: String) =
        listOf("entry", "find", "--json", "--date", date, "--time", time, "--text=${oneLine(text)}")

    fun edit(entry: TimelineEntry, newDate: String, newTime: String, newText: String): List<String> {
        val args = mutableListOf("entry", "edit", "--json", "--date", entry.date, "--time", entry.time, "--text=${entry.text}")
        if (newDate != entry.date) args += listOf("--new-date", newDate)
        if (newTime != entry.time) args += listOf("--new-time", newTime)
        if (oneLine(newText) != entry.text) args += "--new-text=${oneLine(newText)}"
        return args
    }

    fun delete(entry: TimelineEntry) =
        listOf("entry", "delete", "--json", "--date", entry.date, "--time", entry.time, "--text=${entry.text}")
}

/** Reading memory_tool's JSON answers. */
object PcReplies {
    /** The last line that parses as a JSON object; the CLI prints only that line with --json. */
    fun lastJson(stdout: String): JSONObject? {
        for (line in stdout.lines().map { it.trim() }.asReversed()) {
            if (!line.startsWith("{")) continue
            return try {
                JSONObject(line)
            } catch (e: Exception) {
                continue
            }
        }
        return null
    }

    /** The PC's memory_tool is older than the command the app used. */
    const val UNSUPPORTED = "unsupported"

    private fun <T> read(stdout: String, stderr: String, value: (JSONObject) -> T?): PcReply<T> {
        val json = lastJson(stdout)
        if (json == null && "No such command" in stdout + stderr) {
            return PcReply.Refused(UNSUPPORTED, "The PC's memory_tool is too old for this; update it to 1.6.0 or later.")
        }
        json ?: return PcReply.Unreadable(
                (stdout.lines() + stderr.lines()).map { it.trim() }.firstOrNull { it.isNotEmpty() }.orEmpty().take(300)
            )
        if (!json.optBoolean("ok", false)) return PcReply.Refused(json.optString("code", "failed"), json.optString("error", ""))
        return value(json)?.let { PcReply.Ok(it) } ?: PcReply.Unreadable(json.toString().take(300))
    }

    private fun entry(o: JSONObject?): TimelineEntry? {
        if (o == null) return null
        val date = o.optString("date")
        val time = o.optString("time")
        if (date.isEmpty() || time.isEmpty()) return null
        return TimelineEntry(date, time, o.optString("text"), strings(o.optJSONArray("tags")))
    }

    private fun strings(a: JSONArray?): List<String> =
        if (a == null) emptyList() else (0 until a.length()).mapNotNull { a.optString(it).takeIf(String::isNotEmpty) }

    /** `days --json`: the days that have entries, as given. */
    fun days(stdout: String, stderr: String): PcReply<List<Day>> = read(stdout, stderr) { json ->
        val days = json.optJSONArray("days") ?: return@read null
        (0 until days.length()).mapNotNull { i ->
            val d = days.optJSONObject(i) ?: return@mapNotNull null
            val list = d.optJSONArray("entries") ?: JSONArray()
            Day(d.optString("date"), (0 until list.length()).mapNotNull { entry(list.optJSONObject(it)) })
        }
    }

    /** `search --json`: the timeline entries found, in the order memory_tool ranked them. */
    fun search(stdout: String, stderr: String): PcReply<List<TimelineEntry>> = read(stdout, stderr) { json ->
        val results = json.optJSONArray("results") ?: return@read null
        (0 until results.length()).mapNotNull { entry(results.optJSONObject(it)?.optJSONObject("entry")) }.distinct()
    }

    /** `entry find --json`: whether the entry is there. */
    fun found(stdout: String, stderr: String): PcReply<Boolean> = read(stdout, stderr) { json ->
        if (json.has("found")) json.optBoolean("found") else null
    }

    /** `entry edit/delete --json`: the entry as it now is (edit) or was (delete), and before an edit. */
    fun changed(stdout: String, stderr: String): PcReply<Pair<TimelineEntry, TimelineEntry?>> = read(stdout, stderr) { json ->
        entry(json.optJSONObject("entry"))?.let { it to entry(json.optJSONObject("previous")) }
    }
}

/** Timeline order for a list: newest day first, and newest entry first within a day. */
fun newestFirst(entries: List<TimelineEntry>): List<TimelineEntry> =
    entries.sortedWith(compareByDescending<TimelineEntry> { it.date }.thenByDescending { normalTime(it.time) })

/** "9:05" and "09:05" sort the same. */
fun normalTime(time: String): String {
    val (h, m) = time.split(":").let { (it.getOrNull(0) ?: "0") to (it.getOrNull(1) ?: "00") }
    return h.padStart(2, '0') + ":" + m
}

/** Keeping the loaded days of the timeline. Pure, so it is tested on the JVM. */
object Days {
    /**
     * Replace the days from [from] to [to] (inclusive, YYYY-MM-DD) with [fresh],
     * the PC's answer for that range, and keep the rest. A day absent from the
     * answer has no entries any more.
     */
    fun merge(current: List<Day>, from: String, to: String, fresh: List<Day>): List<Day> =
        (current.filter { it.date < from || it.date > to } + fresh.filter { it.date in from..to && it.entries.isNotEmpty() })
            .sortedByDescending { it.date }

    /** A day's entries, newest first; of two at the same minute, the one written later first. */
    fun newestFirst(day: Day): List<TimelineEntry> = day.entries.reversed().sortedByDescending { normalTime(it.time) }
}
