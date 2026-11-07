package io.github.hanyki111.memorycapture.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.time.LocalDate

/** The large widget's entries. All data is synthetic. */
class RecentTest {

    private fun e(date: String, time: String, text: String) = TimelineEntry(date, time, text)

    @Test
    fun theNewestThreeAcrossDays() {
        val days = listOf(
            Day("2026-03-01", listOf(e("2026-03-01", "09:00", "a"), e("2026-03-01", "18:00", "b"))),
            Day("2026-03-03", listOf(e("2026-03-03", "8:05", "c"))),
            Day("2026-03-02", listOf(e("2026-03-02", "10:00", "d"), e("2026-03-02", "07:00", "e"))),
        )
        assertEquals(listOf("c", "d", "e"), Recents.latest(days).map { it.text })
        assertEquals(listOf("c", "d", "e", "b", "a"), Recents.latest(days, count = 10).map { it.text })
    }

    @Test
    fun ofTwoAtTheSameMinuteTheLaterWrittenFirst() {
        val day = Day("2026-03-01", listOf(e("2026-03-01", "09:00", "first"), e("2026-03-01", "09:00", "second")))
        assertEquals(listOf("second", "first"), Recents.latest(listOf(day)).map { it.text })
    }

    @Test
    fun noDaysNoEntries() {
        assertEquals(emptyList<TimelineEntry>(), Recents.latest(emptyList()))
    }

    @Test
    fun whatIsWrittenIsReadBack() {
        val recent = Recent(listOf(e("2026-03-01", "09:00", "[태그] \"따옴표\" 'x' \\ 끝"), e("2026-02-28", "23:59", "")), 1_700_000_000_000)
        assertEquals(recent, Recents.fromJson(Recents.toJson(recent)))
    }

    @Test
    fun anythingElseReadsAsNothing() {
        assertNull(Recents.fromJson(null))
        assertNull(Recents.fromJson(""))
        assertNull(Recents.fromJson("not json"))
        assertNull(Recents.fromJson("{\"entries\": []}"))
    }

    @Test
    fun daysAreNamedFromToday() {
        val today = LocalDate.of(2026, 3, 1)
        assertEquals(DayName.Today, DayName.of("2026-03-01", today))
        assertEquals(DayName.Yesterday, DayName.of("2026-02-28", today))
        assertEquals(DayName.Other(LocalDate.of(2026, 2, 27)), DayName.of("2026-02-27", today))
        assertNull(DayName.of("someday", today))
    }
}
