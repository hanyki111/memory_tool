package io.github.hanyki111.memorycapture.core

import org.json.JSONObject

/** What memory_tool said about a record, read from its output. */
sealed class RecordReply {
    /** Recorded. `notices` are messages for the person, such as the review reminder. */
    data class Recorded(val time: String?, val notices: List<String>) : RecordReply()

    /** memory_tool refused, with its failure code; sending again would not help. */
    data class Refused(val code: String, val message: String) : RecordReply()

    /** The output was not memory_tool's JSON: a wrong command, Python missing, and so on. */
    data class Unreadable(val firstLine: String, val exitStatus: Int) : RecordReply()
}

object Replies {
    /**
     * Read the result: the last line that parses as a JSON object.
     *
     * The CLI prints only that line with --json; looking for the last one keeps
     * a stray warning above it from breaking the result.
     */
    fun parse(stdout: String, stderr: String, exitStatus: Int): RecordReply {
        val lines = stdout.lines().map { it.trim() }.filter { it.isNotEmpty() }
        for (line in lines.asReversed()) {
            if (!line.startsWith("{")) continue
            val json = try {
                JSONObject(line)
            } catch (e: Exception) {
                continue
            }
            return fromJson(json)
        }

        val shown = (lines.firstOrNull() ?: stderr.lines().map { it.trim() }.firstOrNull { it.isNotEmpty() }).orEmpty()
        return RecordReply.Unreadable(shown.take(300), exitStatus)
    }

    /**
     * Whether `day --json` output holds the entry, by date, time and text.
     * Null when the output is not a successful answer.
     */
    fun dayHas(stdout: String, date: String, time: String, text: String): Boolean? {
        val json = lastJson(stdout) ?: return null
        if (!json.optBoolean("ok", false)) return null
        val days = json.optJSONArray("days") ?: return null
        val wanted = oneLine(text)
        for (d in 0 until days.length()) {
            val entries = days.optJSONObject(d)?.optJSONArray("entries") ?: continue
            for (e in 0 until entries.length()) {
                val found = entries.optJSONObject(e) ?: continue
                if (found.optString("date") == date && found.optString("time") == time && found.optString("text").trim() == wanted) {
                    return true
                }
            }
        }
        return false
    }

    private fun lastJson(stdout: String): JSONObject? {
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

    private fun fromJson(json: JSONObject): RecordReply {
        if (!json.optBoolean("ok", false)) {
            return RecordReply.Refused(json.optString("code", "failed"), json.optString("error", ""))
        }
        val time = json.optJSONObject("entry")?.optString("time")?.takeIf { it.isNotEmpty() }
        val notices = mutableListOf<String>()
        val array = json.optJSONArray("notices")
        if (array != null) {
            for (i in 0 until array.length()) {
                array.optJSONObject(i)?.optString("message")?.takeIf { it.isNotEmpty() }?.let(notices::add)
            }
        }
        return RecordReply.Recorded(time, notices)
    }
}
