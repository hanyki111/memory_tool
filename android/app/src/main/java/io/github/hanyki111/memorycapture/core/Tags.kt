package io.github.hanyki111.memorycapture.core

/**
 * Tags offered as chips after speech: the ones used lately, from the entries
 * the phone knows. No Android API here, so the JVM tests cover it.
 */
object Tags {
    private val HASH = Regex("""(?<![\w\[])#([\w가-힣-]+)""")

    /**
     * The tags in an entry: `[tag]`s at the start, as the PC stores them, and
     * `#tag`s anywhere, as a person writes them before the PC rewrites them.
     */
    fun of(text: String): List<String> =
        (leadingTags(text).first + HASH.findAll(text).map { it.groupValues[1] }).filter { it.isNotBlank() }

    /** The tags of these entries, newest entry first, each once (ignoring case), at most [limit]. */
    fun recent(textsNewestFirst: List<String>, limit: Int = 8): List<String> {
        val seen = mutableSetOf<String>()
        val tags = mutableListOf<String>()
        for (text in textsNewestFirst) {
            for (tag in of(text)) {
                if (seen.add(tag.lowercase())) tags += tag
                if (tags.size == limit) return tags
            }
        }
        return tags
    }

    /** The leading tags and the rest; unlike [leadingTags], text that is only tags still gives its tags. */
    private fun split(text: String): Pair<List<String>, String> {
        val (tags, rest) = leadingTags(text.trim() + " " + END)
        return tags to rest.removeSuffix(END).trim()
    }

    /** A mark no entry holds, so the text is never only tags */
    private const val END = "\u0001"

    /** Whether the entry starts with this tag. */
    fun has(text: String, tag: String): Boolean =
        split(text).first.any { it.equals(tag, ignoreCase = true) }

    /** Put the tag before the text, or take it away when it is there already. */
    fun toggle(text: String, tag: String): String {
        val (tags, body) = split(text)
        val kept = if (tags.any { it.equals(tag, ignoreCase = true) }) tags.filterNot { it.equals(tag, ignoreCase = true) } else tags + tag
        return (kept.joinToString(" ") { "[$it]" } + " " + body).trim()
    }
}
