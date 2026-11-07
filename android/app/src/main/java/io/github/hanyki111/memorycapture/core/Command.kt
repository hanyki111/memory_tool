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

/**
 * A macOS or Linux PC: its SSH login shell is sh, bash or zsh, which all read
 * single quotes the same way. Nothing is expanded inside them; a quote itself
 * is closed, escaped and opened again: it's → 'it'\''s'.
 */
object Sh {
    fun quote(value: String): String = "'" + value.replace("'", "'\\''") + "'"
}

/** The PC's system, which decides the shell the command is written for. */
enum class PcKind(val key: String) {
    WINDOWS("windows"), POSIX("posix");

    fun quote(value: String) = if (this == WINDOWS) PowerShell.quote(value) else Sh.quote(value)

    /** The line sent over SSH. PowerShell gets it in Base64 (see [PowerShell.forTransport]); sh as it is. */
    fun transport(command: String) = if (this == WINDOWS) PowerShell.forTransport(command) else command

    companion object {
        fun of(key: String?) = entries.firstOrNull { it.key == key } ?: WINDOWS
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
class CommandTemplate private constructor(val text: String, val kind: PcKind) {

    /** The full command line for these arguments, each quoted for the PC's shell. */
    fun fill(args: List<String>): String =
        text.replace(PLACEHOLDER, args.joinToString(" ") { kind.quote(it) })

    /** What is sent over SSH for these arguments. */
    fun line(args: List<String>): String = kind.transport(fill(args))

    companion object {
        const val PLACEHOLDER = "{args}"

        /** Check a template; it must hold `{args}` exactly once. */
        fun parse(text: String, kind: PcKind = PcKind.WINDOWS): Result<CommandTemplate> {
            val trimmed = text.trim()
            val count = trimmed.windowed(PLACEHOLDER.length).count { it == PLACEHOLDER }
            return when {
                trimmed.isEmpty() -> Result.failure(IllegalArgumentException("The command is empty"))
                count == 0 -> Result.failure(IllegalArgumentException("The command needs $PLACEHOLDER where the arguments go"))
                count > 1 -> Result.failure(IllegalArgumentException("The command may hold $PLACEHOLDER only once"))
                else -> Result.success(CommandTemplate(trimmed, kind))
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
    const val RUN_POSIX = "python3 -m memory_tool"

    /** Why this folder cannot be used, or null when it can. */
    fun problem(path: String): String? = when {
        path.isBlank() -> "The folder is empty"
        path.any { it == '\n' || it == '\r' } -> "The folder must be one line"
        CommandTemplate.PLACEHOLDER in path -> "The folder may not hold ${CommandTemplate.PLACEHOLDER}"
        else -> null
    }

    /**
     * The command that runs memory_tool in this folder; [run] starts memory_tool.
     * On macOS and Linux `&&` stops at a wrong folder, and Python is told to
     * write UTF-8 whatever the session's locale.
     */
    fun command(path: String, kind: PcKind = PcKind.WINDOWS, run: String? = null): CommandTemplate {
        problem(path)?.let { throw IllegalArgumentException(it) }
        val folder = kind.quote(path.trim())
        val text = when (kind) {
            PcKind.WINDOWS -> "Set-Location -LiteralPath $folder -ErrorAction Stop; ${run ?: RUN} ${CommandTemplate.PLACEHOLDER}"
            PcKind.POSIX -> "cd -- $folder && export PYTHONIOENCODING=utf-8 && exec ${run ?: RUN_POSIX} ${CommandTemplate.PLACEHOLDER}"
        }
        return CommandTemplate.parse(text, kind).getOrThrow()
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
