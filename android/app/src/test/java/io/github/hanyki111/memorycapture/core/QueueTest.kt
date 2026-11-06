package io.github.hanyki111.memorycapture.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class QueueTest {

    private val entry = Entry(id = "1", text = "기록", date = "2026-11-07", time = "09:05")

    // ---- reading replies ----------------------------------------------------

    @Test
    fun recordedWithNotices() {
        val reply = Replies.parse(
            """warning above
            {"ok": true, "entry": {"date": "2026-11-07", "time": "09:05", "text": "기록", "tags": []}, "path": "x", "notices": [{"kind": "review", "message": "리뷰할 때입니다"}]}""",
            "", 0,
        )
        assertEquals(RecordReply.Recorded("09:05", listOf("리뷰할 때입니다")), reply)
    }

    @Test
    fun refusedWithCode() {
        val reply = Replies.parse("""{"ok": false, "code": "distant_past", "error": "Too old"}""", "", 1)
        assertEquals(RecordReply.Refused("distant_past", "Too old"), reply)
    }

    @Test
    fun outputThatIsNotJson() {
        assertEquals(
            RecordReply.Unreadable("python: command not found", 1),
            Replies.parse("", "\npython: command not found\n", 1),
        )
        assertEquals(RecordReply.Unreadable("", 0), Replies.parse("", "", 0))
    }

    // ---- state changes ------------------------------------------------------

    @Test
    fun notSentStaysWaiting() {
        val (next, reply) = Transitions.applyOutcome(entry, Outcome.NotSent("No connection"), 10)
        assertEquals(State.PENDING, next.state)
        assertEquals(1, next.attempts)
        assertFalse(next.maybeRecorded)
        assertNull(reply)
    }

    @Test
    fun uncertainNeedsThePerson() {
        val (next, _) = Transitions.applyOutcome(entry, Outcome.Uncertain("Connection lost after sending"), 10)
        assertEquals(State.ATTENTION, next.state)
        assertTrue(next.maybeRecorded)
    }

    @Test
    fun recordedIsSent() {
        val (next, reply) = Transitions.applyOutcome(entry, Outcome.Ran("""{"ok": true, "entry": {"time": "09:05"}, "notices": []}""", "", 0), 10)
        assertEquals(State.SENT, next.state)
        assertTrue(reply is RecordReply.Recorded)
    }

    @Test
    fun refusedNeedsThePersonAndWasNotRecorded() {
        val (next, _) = Transitions.applyOutcome(entry, Outcome.Ran("""{"ok": false, "code": "distant_past", "error": "Too old"}""", "", 1), 10)
        assertEquals(State.ATTENTION, next.state)
        assertFalse(next.maybeRecorded)
        assertEquals("Too old", next.note)
    }

    @Test
    fun theOldestWaitingEntryGoesFirst() {
        val entries = listOf(
            entry.copy(id = "b", time = "10:00"),
            entry.copy(id = "a", time = "09:00"),
            entry.copy(id = "c", time = "08:00", state = State.ATTENTION),
            entry.copy(id = "d", date = "2026-11-06", time = "23:00", state = State.SENT),
        )
        assertEquals("a", Transitions.next(entries)?.id)
    }

    @Test
    fun theRecentlySentListIsCapped() {
        val sent = (1..60).map { entry.copy(id = "s$it", state = State.SENT, changedAt = it.toLong()) }
        val waiting = entry.copy(id = "w")
        val kept = Transitions.trim(sent + waiting)

        assertEquals(Transitions.KEEP_SENT + 1, kept.size)
        assertTrue(kept.any { it.id == "w" })
        assertTrue(kept.none { it.id == "s1" })
    }

    @Test
    fun markSentAndResend() {
        val attention = entry.copy(state = State.ATTENTION, maybeRecorded = true, note = "x")
        assertEquals(State.SENT, Transitions.markSent(attention, 1).state)
        val again = Transitions.resend(attention, 1)
        assertEquals(State.PENDING, again.state)
        assertFalse(again.maybeRecorded)
    }

    @Test
    fun storedFormRoundTrips() {
        val entries = listOf(entry, entry.copy(id = "2", text = "따옴표 \" '와 줄", state = State.ATTENTION, attempts = 3, note = "n", maybeRecorded = true, changedAt = 99))
        assertEquals(entries, EntryJson.read(EntryJson.write(entries)))
        assertEquals(emptyList<Entry>(), EntryJson.read(""))
    }

    @Test
    fun `retry waits a fixed step longer each time, up to five minutes`() {
        assertEquals(15L, Retry.delaySeconds(0))
        assertEquals(15L, Retry.delaySeconds(1))
        assertEquals(45L, Retry.delaySeconds(3))
        assertEquals(300L, Retry.delaySeconds(20))
        assertEquals(300L, Retry.delaySeconds(1000))
    }
}
