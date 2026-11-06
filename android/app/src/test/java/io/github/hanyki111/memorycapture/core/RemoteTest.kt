package io.github.hanyki111.memorycapture.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RemoteTest {
    private val entry = TimelineEntry("2026-11-07", "09:05", "[버그] 로그인 오류", listOf("버그"))

    // ---- arguments ----------------------------------------------------------

    @Test
    fun valuesAPersonWroteStayInOneArgument() {
        assertEquals(
            listOf("entry", "find", "--json", "--date", "2026-11-07", "--time", "09:05", "--text=-대시 #tag"),
            PcArgs.find("2026-11-07", "09:05", "-대시\n#tag"),
        )
        assertEquals(listOf("search", "--json", "--no-cache", "--type", "timeline", "--", "--json 검색"), PcArgs.search(" --json\n검색 "))
    }

    @Test
    fun editSendsOnlyWhatChanged() {
        val base = listOf("entry", "edit", "--json", "--date", "2026-11-07", "--time", "09:05", "--text=[버그] 로그인 오류")
        assertEquals(base, PcArgs.edit(entry, "2026-11-07", "09:05", "[버그] 로그인 오류"))
        assertEquals(base + "--new-text=-고침", PcArgs.edit(entry, "2026-11-07", "09:05", "-고침"))
        assertEquals(base + listOf("--new-date", "2026-11-06", "--new-time", "23:50"), PcArgs.edit(entry, "2026-11-06", "23:50", entry.text))
    }

    @Test
    fun deleteNamesTheEntryAsListed() {
        assertEquals(
            listOf("entry", "delete", "--json", "--date", "2026-11-07", "--time", "09:05", "--text=[버그] 로그인 오류"),
            PcArgs.delete(entry),
        )
    }

    // ---- replies ------------------------------------------------------------

    @Test
    fun readsDays() {
        val out = """warning
            {"ok": true, "from": "2026-11-06", "to": "2026-11-07", "days": [{"date": "2026-11-07", "path": "x", "entries": [{"date": "2026-11-07", "time": "09:05", "text": "[버그] 로그인 오류", "tags": ["버그"]}, {"date": "2026-11-07", "time": "9:30", "text": "둘째", "tags": []}], "content": ""}]}"""
        val days = (PcReplies.days(out, "") as PcReply.Ok).value
        assertEquals(listOf(Day("2026-11-07", listOf(entry, TimelineEntry("2026-11-07", "9:30", "둘째")))), days)
    }

    @Test
    fun readsSearchResultsWithEntriesOnly() {
        val out = """{"ok": true, "query": "q", "results": [""" +
            """{"kind": "timeline", "entry": {"date": "2026-11-07", "time": "09:05", "text": "[버그] 로그인 오류", "tags": ["버그"]}},""" +
            """{"kind": "module", "entry": null},""" +
            """{"kind": "timeline", "entry": {"date": "2026-11-07", "time": "09:05", "text": "[버그] 로그인 오류", "tags": ["버그"]}}]}"""
        assertEquals(PcReply.Ok(listOf(entry)), PcReplies.search(out, ""))
    }

    @Test
    fun readsChangesAndRefusals() {
        val edited = """{"ok": true, "entry": {"date": "2026-11-06", "time": "23:50", "text": "고침", "tags": []}, "previous": {"date": "2026-11-07", "time": "09:05", "text": "[버그] 로그인 오류", "tags": ["버그"]}}"""
        assertEquals(PcReply.Ok(TimelineEntry("2026-11-06", "23:50", "고침") to entry), PcReplies.changed(edited, ""))
        assertEquals(PcReply.Refused("not_found", "gone"), PcReplies.changed("""{"ok": false, "code": "not_found", "error": "gone"}""", ""))
        assertEquals(PcReply.Unreadable("python: not found"), PcReplies.changed("", "\npython: not found\n"))
        val old = PcReplies.changed("", "Usage: python -m memory_tool\nError: No such command 'entry'.")
        assertTrue(old.toString(), old is PcReply.Refused && old.code == PcReplies.UNSUPPORTED)
    }

    // ---- keeping the loaded days ----------------------------------------------

    @Test
    fun mergeReplacesTheRangeAndKeepsTheRest() {
        fun day(date: String, vararg texts: String) = Day(date, texts.map { TimelineEntry(date, "10:00", it) })
        val loaded = listOf(day("2026-11-07", "a"), day("2026-11-05", "b"), day("2026-10-30", "c"))

        val merged = Days.merge(loaded, "2026-11-04", "2026-11-07", listOf(day("2026-11-06", "new"), day("2026-11-07", "a2")))
        assertEquals(listOf("2026-11-07", "2026-11-06", "2026-10-30"), merged.map { it.date })
        assertEquals("a2", merged[0].entries.single().text)

        val older = Days.merge(merged, "2026-10-24", "2026-10-29", listOf(day("2026-10-25", "d")))
        assertEquals("2026-10-25", older.last().date)
    }

    @Test
    fun newestFirstWithinADay() {
        val day = Day("2026-11-07", listOf(
            TimelineEntry("2026-11-07", "9:05", "early"),
            TimelineEntry("2026-11-07", "10:00", "first at ten"),
            TimelineEntry("2026-11-07", "10:00", "second at ten"),
            TimelineEntry("2026-11-07", "08:00", "written late"),
        ))
        assertEquals(listOf("second at ten", "first at ten", "early", "written late"), Days.newestFirst(day).map { it.text })
    }

    @Test
    fun newestFirstAcrossDays() {
        val list = newestFirst(listOf(
            TimelineEntry("2026-11-06", "23:00", "a"),
            TimelineEntry("2026-11-07", "9:00", "b"),
            TimelineEntry("2026-11-07", "10:00", "c"),
        ))
        assertEquals(listOf("c", "b", "a"), list.map { it.text })
    }
}
