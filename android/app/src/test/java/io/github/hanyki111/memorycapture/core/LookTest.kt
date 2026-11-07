package io.github.hanyki111.memorycapture.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LookTest {

    @Test
    fun leadingTagsBecomeChips() {
        assertEquals(listOf("idea") to "weekly template", leadingTags("[idea] weekly template"))
        assertEquals(listOf("버그", "긴급") to "위젯 글자", leadingTags("[버그] [긴급] 위젯 글자"))
        assertEquals(listOf("a", "b") to "x", leadingTags("[a][b] x"))
    }

    @Test
    fun onlyTheStartIsTags() {
        assertEquals(emptyList<String>() to "fix [bug] later", leadingTags("fix [bug] later"))
        assertEquals(emptyList<String>() to "[] empty", leadingTags("[] empty"))
        assertEquals(emptyList<String>() to "[open bracket", leadingTags("[open bracket"))
        // Only tags: they stay the text, so the entry still shows something.
        assertEquals(emptyList<String>() to "[only]", leadingTags("[only]"))
    }

    @Test
    fun modesAndAccentsReadBackAndFallBack() {
        Mode.entries.forEach { assertEquals(it, Mode.of(it.key)) }
        Accent.entries.forEach { assertEquals(it, Accent.of(it.key)) }
        assertEquals(Mode.SYSTEM, Mode.of(null))
        assertEquals(Accent.DYNAMIC, Accent.of("gone"))
        assertTrue(Mode.SYSTEM.isDark(true) && !Mode.SYSTEM.isDark(false))
        assertTrue(Mode.DARK.isDark(false) && !Mode.LIGHT.isDark(true))
    }

    @Test
    fun blendMixesEachChannel() {
        assertEquals(0xFFFFFFFF, blend(0xFFFFFFFF, 0xFF000000, 0.0))
        assertEquals(0xFF000000, blend(0xFFFFFFFF, 0xFF000000, 1.0))
        assertEquals(0xFF808080, blend(0xFFFFFFFF, 0xFF000000, 0.5))
    }

    /** Text on the background and the accents keeps 4.5:1, light and dark. */
    @Test
    fun colorsKeepTheirContrast() {
        for (dark in listOf(false, true)) {
            val n = Neutrals.of(dark)
            assertTrue("text", contrast(n.text, n.background) >= 4.5)
            assertTrue("muted", contrast(n.muted, n.background) >= 4.5)
            assertTrue("muted raised", contrast(n.muted, n.raised) >= 4.5)
            Accent.entries.forEach { a ->
                val c = a.color(dark)
                assertTrue("$a on background", contrast(c, n.background) >= 4.5)
                assertTrue("$a under its text", contrast(n.onAccent, c) >= 4.5)
            }
        }
    }

    private fun contrast(a: Long, b: Long): Double {
        fun lum(c: Long): Double {
            fun ch(shift: Int): Double {
                val v = ((c shr shift) and 0xFF) / 255.0
                return if (v <= 0.03928) v / 12.92 else Math.pow((v + 0.055) / 1.055, 2.4)
            }
            return 0.2126 * ch(16) + 0.7152 * ch(8) + 0.0722 * ch(0)
        }
        val (hi, lo) = listOf(lum(a), lum(b)).sortedDescending()
        return (hi + 0.05) / (lo + 0.05)
    }
}
