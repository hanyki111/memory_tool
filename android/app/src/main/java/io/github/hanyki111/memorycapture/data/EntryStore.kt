package io.github.hanyki111.memorycapture.data

import android.content.Context
import io.github.hanyki111.memorycapture.core.Entry
import io.github.hanyki111.memorycapture.core.EntryJson
import io.github.hanyki111.memorycapture.core.State
import io.github.hanyki111.memorycapture.core.Transitions
import java.io.File
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.UUID

/**
 * The entries on the phone, in one JSON file.
 *
 * Every change is written at once, with a temporary file renamed over the old
 * one, so an entry is never lost to a half-written file.
 */
object EntryStore {
    private val listeners = mutableListOf<() -> Unit>()
    private val DATE = DateTimeFormatter.ofPattern("yyyy-MM-dd")
    private val TIME = DateTimeFormatter.ofPattern("HH:mm")

    private fun file(context: Context) = File(context.applicationContext.filesDir, "entries.json")

    @Synchronized
    fun all(context: Context): List<Entry> {
        val f = file(context)
        return if (f.isFile) runCatching { EntryJson.read(f.readText()) }.getOrDefault(emptyList()) else emptyList()
    }

    /** Keep a new entry, dated now. */
    fun add(context: Context, text: String): Entry {
        val now = LocalDateTime.now()
        val entry = Entry(
            id = UUID.randomUUID().toString(),
            text = text,
            date = now.format(DATE),
            time = now.format(TIME),
            changedAt = System.currentTimeMillis(),
        )
        change(context) { it + entry }
        return entry
    }

    /** Replace one entry by its id. */
    fun put(context: Context, entry: Entry) = change(context) { list -> list.map { if (it.id == entry.id) entry else it } }

    fun remove(context: Context, id: String) = change(context) { list -> list.filterNot { it.id == id } }

    fun counts(context: Context): Pair<Int, Int> {
        val entries = all(context)
        return entries.count { it.state == State.PENDING } to entries.count { it.state == State.ATTENTION }
    }

    @Synchronized
    private fun change(context: Context, transform: (List<Entry>) -> List<Entry>) {
        val next = Transitions.trim(transform(all(context)))
        val f = file(context)
        val temp = File(f.parentFile, f.name + ".tmp")
        temp.writeText(EntryJson.write(next))
        if (!temp.renameTo(f)) {
            f.delete()
            temp.renameTo(f)
        }
        listeners.toList().forEach { it() }
    }

    @Synchronized
    fun listen(listener: () -> Unit) {
        listeners.add(listener)
    }

    @Synchronized
    fun unlisten(listener: () -> Unit) {
        listeners.remove(listener)
    }
}
