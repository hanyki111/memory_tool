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
 * The knowledge base on the PC: the person sets only its folder, and the app
 * runs memory_tool there.
 *
 * Set-Location stops the command when the folder is wrong. Without
 * `-ErrorAction Stop` PowerShell would report the error and go on, and
 * memory_tool would run in the SSH session's home folder instead.
 */
object KnowledgeBase {
    const val RUN = "python -m memory_tool"

    /** Why this folder cannot be used, or null when it can. */
    fun problem(path: String): String? = when {
        path.isBlank() -> "The folder is empty"
        path.any { it == '\n' || it == '\r' } -> "The folder must be one line"
        CommandTemplate.PLACEHOLDER in path -> "The folder may not hold ${CommandTemplate.PLACEHOLDER}"
        else -> null
    }

    /** The command that runs memory_tool in this folder; [run] starts memory_tool. */
    fun command(path: String, run: String = RUN): CommandTemplate {
        problem(path)?.let { throw IllegalArgumentException(it) }
        return CommandTemplate.parse(
            "Set-Location -LiteralPath ${PowerShell.quote(path.trim())} -ErrorAction Stop; $run ${CommandTemplate.PLACEHOLDER}"
        ).getOrThrow()
    }

    private val SAVED = Regex(
        """^Set-Location\s+(?:-(?:Literal)?Path\s+)?(?:'((?:[^']|'')*)'|"([^"]*)"|(\S+))(?:\s+-ErrorAction\s+Stop)?\s*;\s*python\s+-m\s+memory_tool\s+\{args\}$""",
        RegexOption.IGNORE_CASE,
    )

    /** The folder in a command saved by 0.2 or earlier, or null when it is not one this app made. */
    fun pathFrom(command: String?): String? {
        val match = SAVED.matchEntire(command?.trim() ?: return null) ?: return null
        val (single, double, bare) = match.destructured
        return when {
            single.isNotEmpty() -> single.replace("''", "'")
            double.isNotEmpty() -> double
            else -> bare
        }.takeIf { problem(it) == null }
    }
}

/**
 * The arguments that record one entry at the moment it was written, so an
 * entry sent later still lands at its own time. "--" ends the options, so text
 * starting with "-" stays text.
 */
fun recordArgs(text: String, date: String, time: String): List<String> =
    listOf("record", "--json", "--date", date, "--time", time, "--", oneLine(text))
