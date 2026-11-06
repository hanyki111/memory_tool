package io.github.hanyki111.memorycapture.core

/**
 * Building the command the PC's shell runs.
 *
 * The PC's SSH shell is PowerShell. Every argument goes in as a single-quoted
 * PowerShell string, where nothing is expanded: no `$variable`, no `;`, no
 * backtick escape. Only the quote character itself needs care.
 *
 * No Android API here, so the JVM tests cover it.
 */
object PowerShell {
    /**
     * Characters PowerShell reads as a single quote. Besides `'`, it takes the
     * typographic quotes too, which phone keyboards often insert.
     */
    private val SINGLE_QUOTES = setOf('\'', '\u2018', '\u2019', '\u201A', '\u201B')

    /** Quote one argument so PowerShell passes it on exactly as written. */
    fun quote(value: String): String {
        val body = StringBuilder(value.length + 2)
        for (c in value) {
            body.append(c)
            if (c in SINGLE_QUOTES) body.append(c) // doubled quote = literal quote
        }
        return "'$body'"
    }

    /**
     * The line actually sent over SSH: the command in Base64, decoded and run by
     * PowerShell on the PC.
     *
     * OpenSSH on Windows hands the command to PowerShell through a Windows
     * command line, where double quotes are taken apart and non-ASCII text
     * depends on code pages. Base64 is letters, digits, + / and =, so nothing
     * on that way can change it. The command then runs with UTF-8 output, so
     * memory_tool's JSON comes back as written.
     */
    fun forTransport(command: String): String {
        val script = "[Console]::OutputEncoding = [Text.Encoding]::UTF8; " +
            "\$OutputEncoding = [Text.Encoding]::UTF8; " +
            "\$env:PYTHONIOENCODING = 'utf-8'; " +
            command
        val encoded = java.util.Base64.getEncoder().encodeToString(script.toByteArray(Charsets.UTF_8))
        return "iex ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$encoded')))"
    }
}

/** A timeline entry is one line: line breaks become spaces. */
fun oneLine(text: String): String = text.replace(Regex("[\\r\\n]+"), " ").trim()

/**
 * The saved way of running memory_tool on the PC, with `{args}` where the
 * arguments go. For example:
 *
 *     Set-Location 'E:\notes'; python -m memory_tool {args}
 */
class CommandTemplate private constructor(val text: String) {

    /** The full command line for these arguments, each quoted for PowerShell. */
    fun fill(args: List<String>): String =
        text.replace(PLACEHOLDER, args.joinToString(" ") { PowerShell.quote(it) })

    companion object {
        const val PLACEHOLDER = "{args}"

        const val DEFAULT = "Set-Location 'E:\\code_projects\\memory_notion'; python -m memory_tool {args}"

        /** Check a template; it must hold `{args}` exactly once. */
        fun parse(text: String): Result<CommandTemplate> {
            val trimmed = text.trim()
            val count = trimmed.windowed(PLACEHOLDER.length).count { it == PLACEHOLDER }
            return when {
                trimmed.isEmpty() -> Result.failure(IllegalArgumentException("The command is empty"))
                count == 0 -> Result.failure(IllegalArgumentException("The command needs $PLACEHOLDER where the arguments go"))
                count > 1 -> Result.failure(IllegalArgumentException("The command may hold $PLACEHOLDER only once"))
                else -> Result.success(CommandTemplate(trimmed))
            }
        }
    }
}

/**
 * The arguments that record one entry at the moment it was written, so an
 * entry sent later still lands at its own time. "--" ends the options, so text
 * starting with "-" stays text.
 */
fun recordArgs(text: String, date: String, time: String): List<String> =
    listOf("record", "--json", "--date", date, "--time", time, "--", oneLine(text))

/** memory_tool's arguments to read one day of the timeline as JSON. */
fun dayArgs(date: String): List<String> = listOf("day", "--json", "--", date)
