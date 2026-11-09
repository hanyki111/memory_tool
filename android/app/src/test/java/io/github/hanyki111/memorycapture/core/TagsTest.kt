package io.github.hanyki111.memorycapture.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Tags offered after speech. All data is synthetic. */
class TagsTest {

    @Test
    fun tagsAtTheStartAndHashTagsAnywhere() {
        assertEquals(listOf("회의", "긴급"), Tags.of("[회의] [긴급] 내일 일정"))
        assertEquals(listOf("idea", "버그"), Tags.of("정리하기 #idea #버그"))
        assertEquals(listOf("a", "b"), Tags.of("[a] 글 #b"))
        assertEquals(emptyList<String>(), Tags.of("글 [중간] 괄호와 이메일a#b"))
    }

    @Test
    fun recentTagsComeNewestFirstOnce() {
        val texts = listOf("[회의] 오늘", "글 #Idea", "[회의] 어제", "[idea] 그제", "[운동] 달리기")
        assertEquals(listOf("회의", "Idea", "운동"), Tags.recent(texts))
        assertEquals(listOf("회의", "Idea"), Tags.recent(texts, limit = 2))
        assertEquals(emptyList<String>(), Tags.recent(listOf("태그 없는 글")))
    }

    @Test
    fun toggleAddsBeforeTheTextAndTakesAway() {
        assertEquals("[회의] 내일 일정", Tags.toggle("내일 일정", "회의"))
        assertEquals("[회의] [긴급] 내일 일정", Tags.toggle("[회의] 내일 일정", "긴급"))
        assertEquals("[긴급] 내일 일정", Tags.toggle("[회의] [긴급] 내일 일정", "회의"))
        assertEquals("내일 일정", Tags.toggle("[회의] 내일 일정", "회의"))
        assertEquals("[회의]", Tags.toggle("", "회의"))
        assertEquals("", Tags.toggle("[회의]", "회의"))
        assertEquals("[회의] [긴급]", Tags.toggle("[회의]", "긴급"))
        assertTrue(Tags.has("[회의] 글", "회의"))
        assertFalse(Tags.has("글 [회의]", "회의"))
    }
}
