package io.github.hanyki111.memorycapture.core

import org.json.JSONArray
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files
import java.util.concurrent.TimeUnit

class CommandTest {

    @Test
    fun quotesEverySingleQuoteKind() {
        assertEquals("'a''b'", PowerShell.quote("a'b"))
        assertEquals("'it’’s'", PowerShell.quote("it’s"))
        assertEquals("'‘‘x‚‚‛‛'", PowerShell.quote("‘x‚‛"))
        assertEquals("''", PowerShell.quote(""))
    }

    @Test
    fun leavesEverythingElseAsWritten() {
        val text = "\$HOME; rm x `n \"q\" %PATH% & | > 한글 🙂"
        assertEquals("'$text'", PowerShell.quote(text))
    }

    @Test
    fun oneLineJoinsLines() {
        assertEquals("a b c", oneLine(" a\r\nb\n\nc "))
    }

    @Test
    fun recordArgsEndOptionsBeforeTheText() {
        assertEquals(
            listOf("record", "--json", "--date", "2026-11-07", "--time", "09:05", "--", "-dash first"),
            recordArgs("-dash first", "2026-11-07", "09:05"),
        )
    }

    @Test
    fun templateNeedsArgsExactlyOnce() {
        assertTrue(CommandTemplate.parse("python -m memory_tool {args}").isSuccess)
        assertTrue(CommandTemplate.parse("python -m memory_tool").isFailure)
        assertTrue(CommandTemplate.parse("{args} {args}").isFailure)
        assertTrue(CommandTemplate.parse("   ").isFailure)
    }

    @Test
    fun fillQuotesEachArgument() {
        val template = CommandTemplate.parse("m {args}").getOrThrow()
        assertEquals("m 'record' '--' 'it''s'", template.fill(listOf("record", "--", "it's")))
    }

    @Test
    fun theTransportLineIsPlainAscii() {
        val line = PowerShell.forTransport("python -m memory_tool 'record' '--' '따옴표 \"큰\"'")
        assertTrue(line, line.all { it.code in 0x20..0x7E })
        assertTrue(line, '"' !in line)
    }

    /**
     * The real path on the PC: OpenSSH hands the line to PowerShell 7
     * (`pwsh -c <line>`), which starts Python. Python echoes its arguments as
     * UTF-8 JSON, not ASCII-escaped, so the way back is checked too. Runs only
     * where pwsh and python exist.
     */
    @Test
    fun powerShellPassesTheTextToPythonAndBackUnchanged() {
        val pwsh = findOnPath("pwsh")
        val python = findOnPath("python")
        assumeTrue("pwsh and python are needed", pwsh != null && python != null)

        val script = Files.createTempFile("argv", ".py").toFile()
        try {
            script.writeText(
                "import sys, json\n" +
                    "sys.stdout.buffer.write((json.dumps(sys.argv[1:], ensure_ascii=False) + '\\n').encode('utf-8'))\n"
            )
            val template = CommandTemplate.parse("& '${python!!.path}' '${script.path}' {args}").getOrThrow()
            val texts = listOf(
                "따옴표 \"큰\" '작은' \u2018둥근\u2019 100% \$HOME %PATH% & | > ^ \\ ` ; 끝",
                "\"only quotes\"",
                "-starts with a dash",
                "emoji 🙂 and tab\there",
                "",
            )
            val line = PowerShell.forTransport(template.fill(listOf("--") + texts))

            val process = ProcessBuilder(pwsh!!.path, "-NoProfile", "-NonInteractive", "-c", line)
                .redirectErrorStream(true)
                .start()
            val output = process.inputStream.readBytes().toString(Charsets.UTF_8)
            assertTrue("pwsh did not finish", process.waitFor(60, TimeUnit.SECONDS))

            val received = JSONArray(output.trim().lines().last())
            assertEquals(listOf("--") + texts, (0 until received.length()).map { received.getString(it) })
        } finally {
            script.delete()
        }
    }

    /** The whole way, with this checkout's memory_tool on a synthetic knowledge base. */
    @Test
    fun memoryToolRecordsTheEntryAsWritten() {
        val pwsh = findOnPath("pwsh")
        val python = findOnPath("python")
        val repo = File(System.getProperty("user.dir")).absoluteFile.parentFile.parentFile // android/app -> repo
        assumeTrue("pwsh, python and the memory_tool checkout are needed",
            pwsh != null && python != null && File(repo, "memory_tool/cli.py").isFile)

        val root = Files.createTempDirectory("mt-android").toFile()
        try {
            File(root, ".memory-tool.yml").writeText("base: \".memory\"\n")
            File(root, ".memory/timeline").mkdirs()
            File(root, ".memory/config.yaml").writeText("version: '1.0'\n")

            val text = "휴대폰 기록 \"따옴표\" '작은' \$HOME 100% 🙂"
            val template = CommandTemplate.parse(
                "Set-Location '${root.path}'; \$env:PYTHONPATH = '${repo.path}'; & '${python!!.path}' -m memory_tool {args}"
            ).getOrThrow()
            val line = PowerShell.forTransport(template.fill(recordArgs(text, "2026-03-01", "09:05")))

            val process = ProcessBuilder(pwsh!!.path, "-NoProfile", "-NonInteractive", "-c", line).start()
            val stdout = process.inputStream.readBytes().toString(Charsets.UTF_8)
            val stderr = process.errorStream.readBytes().toString(Charsets.UTF_8)
            assertTrue("pwsh did not finish", process.waitFor(60, TimeUnit.SECONDS))

            val reply = Replies.parse(stdout, stderr, process.exitValue())
            assertEquals(stdout + stderr, RecordReply.Recorded("09:05", emptyList()), reply)

            val day = root.walkTopDown().first { it.name.endsWith(".md") && "2026-03" in it.path }
            assertTrue(day.readText(), day.readText().lines().contains("- 09:05 | $text"))

            fun pc(args: List<String>): Pair<String, String> {
                val p = ProcessBuilder(pwsh.path, "-NoProfile", "-NonInteractive", "-c", PowerShell.forTransport(template.fill(args))).start()
                val out = p.inputStream.readBytes().toString(Charsets.UTF_8)
                val err = p.errorStream.readBytes().toString(Charsets.UTF_8)
                assertTrue("pwsh did not finish", p.waitFor(60, TimeUnit.SECONDS))
                return out to err
            }

            // memory_tool rewrites tags as it records; the check after a broken connection still finds it.
            val tagged = "끝 태그 #idea #work"
            pc(recordArgs(tagged, "2026-03-01", "09:10"))
            val (foundOut, foundErr) = pc(PcArgs.find("2026-03-01", "09:10", tagged))
            assertEquals(foundOut + foundErr, PcReply.Ok(true), PcReplies.found(foundOut, foundErr))
            val (absentOut, absentErr) = pc(PcArgs.find("2026-03-01", "09:11", tagged))
            assertEquals(PcReply.Ok(false), PcReplies.found(absentOut, absentErr))

            // Reading: the day and a search.
            val (daysOut, daysErr) = pc(PcArgs.days("2026-02-27", "2026-03-01"))
            val days = (PcReplies.days(daysOut, daysErr) as PcReply.Ok).value
            assertEquals(listOf("2026-03-01"), days.map { it.date })
            val listed = days.single().entries
            assertEquals(listOf(text, "[idea] [work] 끝 태그"), listed.map { it.text })

            val (searchOut, searchErr) = pc(PcArgs.search("따옴표"))
            assertEquals(searchOut + searchErr, listOf(listed[0]), (PcReplies.search(searchOut, searchErr) as PcReply.Ok).value)

            // Editing what was listed: move it to the day before, with text starting with a dash.
            val (editOut, editErr) = pc(PcArgs.edit(listed[0], "2026-02-28", "23:50", "-고친 글 \"큰\" '작은' \$HOME"))
            val (after, before) = (PcReplies.changed(editOut, editErr) as PcReply.Ok).value
            assertEquals(TimelineEntry("2026-02-28", "23:50", "-고친 글 \"큰\" '작은' \$HOME"), after)
            assertEquals(listed[0].copy(tags = emptyList()), before)

            // The same edit again: the entry is no longer there.
            val (againOut, againErr) = pc(PcArgs.edit(listed[0], "2026-02-28", "23:50", "x"))
            assertEquals("not_found", (PcReplies.changed(againOut, againErr) as PcReply.Refused).code)

            val (deleteOut, deleteErr) = pc(PcArgs.delete(listed[1]))
            assertTrue(deleteOut + deleteErr, PcReplies.changed(deleteOut, deleteErr) is PcReply.Ok)
            val (leftOut, leftErr) = pc(PcArgs.days("2026-02-27", "2026-03-01"))
            val left = (PcReplies.days(leftOut, leftErr) as PcReply.Ok).value.flatMap { it.entries }
            assertEquals(listOf("-고친 글 \"큰\" '작은' \$HOME"), left.map { it.text })
        } finally {
            root.deleteRecursively()
        }
    }

    private fun findOnPath(name: String): File? {
        val exts = if (System.getProperty("os.name").startsWith("Windows")) listOf(".exe", "") else listOf("")
        return System.getenv("PATH").orEmpty().split(File.pathSeparator)
            .flatMap { dir -> exts.map { File(dir, name + it) } }
            .firstOrNull { it.isFile }
    }
}
