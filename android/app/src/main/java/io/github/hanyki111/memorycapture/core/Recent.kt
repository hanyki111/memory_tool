package io.github.hanyki111.memorycapture.core

import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate

/**
 * The PC's latest entries, kept for the large widget, which shows them while
 * the app is closed. Only these few entries and when they were fetched are
 * kept. No Android API here, so the JVM tests cover it.
 */
data class Recent(val entries: List<TimelineEntry>, val fetchedAt: Long)

object Recents {
    /** How many days are asked for, to fill the widget after a few quiet days */
    const val DAYS = 30

    /** The newest [count] entries of these days, newest first. */
    fun latest(days: List<Day>, count: Int): List<TimelineEntry> =
        days.sortedByDescending { it.date }.asSequence().flatMap { Days.newestFirst(it).asSequence() }.take(count).toList()

    fun toJson(recent: Recent): String = JSONObject()
        .put("fetchedAt", recent.fetchedAt)
        .put("entries", JSONArray().apply {
            recent.entries.forEach { put(JSONObject().put("date", it.date).put("time", it.time).put("text", it.text)) }
        })
        .toString()

    /** What [toJson] wrote, or null for anything else. */
    fun fromJson(text: String?): Recent? = try {
        val json = JSONObject(text ?: return null)
        val list = json.getJSONArray("entries")
        Recent(
            (0 until list.length()).map { i ->
                list.getJSONObject(i).let { TimelineEntry(it.getString("date"), it.getString("time"), it.getString("text")) }
            },
            json.getLong("fetchedAt"),
        )
    } catch (e: Exception) {
        null
    }
}

/** Which day an entry is, as the widget names it. */
sealed class DayName {
    object Today : DayName()
    object Yesterday : DayName()
    data class Other(val day: LocalDate) : DayName()

    companion object {
        fun of(date: String, today: LocalDate): DayName? {
            val day = runCatching { LocalDate.parse(date) }.getOrNull() ?: return null
            return when (day) {
                today -> Today
                today.minusDays(1) -> Yesterday
                else -> Other(day)
            }
        }
    }
}
