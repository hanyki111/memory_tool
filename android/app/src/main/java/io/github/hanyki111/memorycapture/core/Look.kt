package io.github.hanyki111.memorycapture.core

/**
 * How the app looks: light or dark, and the one accent colour.
 *
 * The screens are almost colourless; the accent marks the newest dot of each
 * day, the tags, the send button and what waits to be sent. Colours are ARGB
 * values, so the widget can use them as well as Compose. No Android API here.
 */
enum class Mode(val key: String) {
    SYSTEM("system"), LIGHT("light"), DARK("dark");

    fun isDark(systemDark: Boolean) = when (this) {
        SYSTEM -> systemDark
        LIGHT -> false
        DARK -> true
    }

    companion object {
        fun of(key: String?) = entries.firstOrNull { it.key == key } ?: SYSTEM
    }
}

/**
 * The accent: the phone's own (taken from the wallpaper, Android 12 and later)
 * or one of the app's. Each has a light and a dark shade, the dark one lighter
 * so it reads on the dark background.
 */
enum class Accent(val key: String, val light: Long, val dark: Long) {
    DYNAMIC("dynamic", 0xFF4352C9, 0xFFAAB4FF), // shown as INDIGO where the phone has none
    INDIGO("indigo", 0xFF4352C9, 0xFFAAB4FF),
    TEAL("teal", 0xFF00696B, 0xFF6FD6D6),
    GREEN("green", 0xFF2E6B30, 0xFF8FD68C),
    AMBER("amber", 0xFF855700, 0xFFF2BD5C),
    ROSE("rose", 0xFFA23B5B, 0xFFFFB0C6),
    INK("ink", 0xFF1A1A1A, 0xFFE8E8E3);

    fun color(dark: Boolean) = if (dark) this.dark else light

    companion object {
        fun of(key: String?) = entries.firstOrNull { it.key == key } ?: DYNAMIC
    }
}

/** The neutral colours around the accent. */
class Neutrals private constructor(
    val background: Long,
    /** Sheets, dialogs and the bottom panel, a step off the background */
    val raised: Long,
    val text: Long,
    /** Times, hints and secondary text; still 4.5:1 on the background */
    val muted: Long,
    /** The timeline's line and the dividers */
    val line: Long,
    /** The ring of an entry's dot */
    val ring: Long,
    /** Text on the accent */
    val onAccent: Long,
) {
    companion object {
        val LIGHT = Neutrals(0xFFFAFAF8, 0xFFF2F2EE, 0xFF1A1A1A, 0xFF62625D, 0xFFDEDED8, 0xFF9A9A94, 0xFFFFFFFF)
        val DARK = Neutrals(0xFF161616, 0xFF202020, 0xFFE8E8E3, 0xFFA3A39C, 0xFF34342F, 0xFF6E6E68, 0xFF161616)

        fun of(dark: Boolean) = if (dark) DARK else LIGHT
    }
}

/** [over] laid on [under] at [amount] (0 to 1), opaque: the tint behind a tag. */
fun blend(under: Long, over: Long, amount: Double): Long {
    fun channel(c: Long, shift: Int) = ((c shr shift) and 0xFF).toDouble()
    fun mix(shift: Int) = Math.round(channel(under, shift) * (1 - amount) + channel(over, shift) * amount) shl shift
    return 0xFF000000 or mix(16) or mix(8) or mix(0)
}

/**
 * The tags written before an entry's text, as `record` stores them: "[a] [b] text"
 * gives (["a", "b"], "text"). Only the start counts; brackets later in the text
 * stay text, and an entry that is only tags keeps them as its text.
 */
fun leadingTags(text: String): Pair<List<String>, String> {
    val tags = mutableListOf<String>()
    var rest = text.trimStart()
    while (rest.startsWith("[")) {
        val end = rest.indexOf(']')
        if (end <= 1) break
        val tag = rest.substring(1, end)
        if (tag.isBlank() || '[' in tag) break
        tags += tag.trim()
        rest = rest.substring(end + 1).trimStart()
    }
    return if (rest.isEmpty()) emptyList<String>() to text.trim() else tags to rest
}
