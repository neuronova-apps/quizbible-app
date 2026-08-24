package com.neuronova.quizbible

import com.neuronova.quizbible.data.local.QuizBibleRuntimeLoader
import com.neuronova.quizbible.data.model.AuditStatus
import com.neuronova.quizbible.data.model.Difficulty
import com.neuronova.quizbible.data.model.DifficultyFilter
import com.neuronova.quizbible.data.model.GameMode
import com.neuronova.quizbible.data.model.QuestionType
import com.neuronova.quizbible.data.model.QuizRuntime
import com.neuronova.quizbible.data.model.Testament
import com.neuronova.quizbible.data.repository.QuizBibleRepository
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.BeforeClass
import org.junit.Test
import java.io.File
import java.io.FileInputStream

class QuizBibleAndroidFunctionalTest {

    companion object {
        private lateinit var runtime: QuizRuntime
        private lateinit var repository: QuizBibleRepository

        @BeforeClass
        @JvmStatic
        fun setUpClass() {
            val assetFile = File("src/main/assets/quiz_bible_protestant_rvr1960_runtime_v1.json")
            assertTrue("Archivo de asset runtime no encontrado", assetFile.exists())

            runtime = FileInputStream(assetFile).use {
                QuizBibleRuntimeLoader.loadFromInputStream(it)
            }
            repository = QuizBibleRepository(runtime)
        }
    }

    @Test
    fun testRuntimeTotalQuestionsAndIntegrity() {
        assertEquals("Total preguntas debe ser 3847", 3847, runtime.totalQuestions)
        assertEquals("Lista de preguntas debe contener 3847 elementos", 3847, runtime.questions.size)

        val uniqueIds = runtime.questions.map { it.id }.toSet()
        assertEquals("Debe haber exactamente 3847 IDs únicos", 3847, uniqueIds.size)
    }

    @Test
    fun testTestamentCounts() {
        val otCount = runtime.questions.count { it.testament == Testament.OT }
        val ntCount = runtime.questions.count { it.testament == Testament.NT }

        assertEquals("Antiguo Testamento debe tener 2620 preguntas", 2620, otCount)
        assertEquals("Nuevo Testamento debe tener 1227 preguntas", 1227, ntCount)
        assertEquals(3847, otCount + ntCount)
    }

    @Test
    fun testQuestionTypeCounts() {
        val mcCount = runtime.questions.count { it.questionType == QuestionType.MULTIPLE_CHOICE }
        val tfCount = runtime.questions.count { it.questionType == QuestionType.TRUE_FALSE }

        assertEquals("MULTIPLE_CHOICE debe tener 3692 preguntas", 3692, mcCount)
        assertEquals("TRUE_FALSE debe tener 155 preguntas", 155, tfCount)
        assertEquals(3847, mcCount + tfCount)
    }

    @Test
    fun testDifficultyDistribution() {
        val basic = runtime.questions.count { it.difficulty == Difficulty.BASIC }
        val intermediate = runtime.questions.count { it.difficulty == Difficulty.INTERMEDIATE }
        val advanced = runtime.questions.count { it.difficulty == Difficulty.ADVANCED }
        val expert = runtime.questions.count { it.difficulty == Difficulty.EXPERT }

        assertEquals(693, basic)
        assertEquals(1437, intermediate)
        assertEquals(1243, advanced)
        assertEquals(474, expert)
        assertEquals(3847, basic + intermediate + advanced + expert)
    }

    @Test
    fun testAuditStatusDistribution() {
        val verified = runtime.questions.count { it.auditStatus == AuditStatus.VERIFIED }
        val inconclusive = runtime.questions.count { it.auditStatus == AuditStatus.INCONCLUSIVE }
        val rc = runtime.questions.count { it.auditStatus == AuditStatus.REQUIRES_CORRECTION }

        assertEquals(2486, verified)
        assertEquals(1361, inconclusive)
        assertEquals(0, rc)
    }

    @Test
    fun testAll11GameModesCounts() {
        assertEquals("Modo AT debe tener 2620 preguntas", 2620, repository.getQuestionsByMode(GameMode.ANTIGUO_TESTAMENTO).size)
        assertEquals("Modo NT debe tener 1227 preguntas", 1227, repository.getQuestionsByMode(GameMode.NUEVO_TESTAMENTO).size)
        assertEquals("Modo AMBOS debe tener 3847 preguntas", 3847, repository.getQuestionsByMode(GameMode.AMBOS_TESTAMENTOS).size)
        assertEquals("Modo PERSONAJES_AT debe tener 1005 preguntas", 1005, repository.getQuestionsByMode(GameMode.PERSONAJES_AT).size)
        assertEquals("Modo PERSONAJES_NT debe tener 343 preguntas", 343, repository.getQuestionsByMode(GameMode.PERSONAJES_NT).size)
        assertEquals("Modo PERSONAJES_AMBOS debe tener 1348 preguntas", 1348, repository.getQuestionsByMode(GameMode.PERSONAJES_AMBOS).size)
        assertEquals("Modo VF_NT debe tener 155 preguntas", 155, repository.getQuestionsByMode(GameMode.VERDADERO_FALSO_NT).size)
        assertEquals("Modo VF_AMBOS debe tener 155 preguntas", 155, repository.getQuestionsByMode(GameMode.VERDADERO_FALSO_AMBOS).size)
        assertEquals("Modo JESUS_PALABRAS debe tener 144 preguntas", 144, repository.getQuestionsByMode(GameMode.JESUS_PALABRAS).size)
        assertEquals("Modo JESUS_MILAGROS debe tener 47 preguntas", 47, repository.getQuestionsByMode(GameMode.JESUS_MILAGROS).size)
        assertEquals("Modo JESUS_PARABOLAS debe tener 37 preguntas", 37, repository.getQuestionsByMode(GameMode.JESUS_PARABOLAS).size)
    }

    @Test
    fun testGameMatchCreation() {
        val match = repository.createGameMatch(GameMode.AMBOS_TESTAMENTOS, DifficultyFilter.ALL, 10)
        assertEquals("La partida debe tener exactamente 10 preguntas", 10, match.size)

        val matchIds = match.map { it.id }.toSet()
        assertEquals("No debe haber preguntas repetidas en la partida", 10, matchIds.size)

        for (q in match) {
            assertTrue("Prompt no debe estar vacío", q.prompt.isNotBlank())
            assertTrue("Explicación no debe estar vacía", q.explanation.isNotBlank())
            assertTrue("Referencia no debe estar vacía", q.referenceDisplay.isNotBlank())

            val optionIds = q.options.map { it.id }
            assertTrue("correctOptionId '${q.correctOptionId}' debe existir en las opciones", q.correctOptionId in optionIds)
        }
    }

    @Test
    fun testOptionShufflingPreservesCorrectOptionValidation() {
        val match = repository.createGameMatch(GameMode.NUEVO_TESTAMENTO, DifficultyFilter.INTERMEDIATE, 10)
        for (q in match) {
            val correctOpt = q.options.find { it.id == q.correctOptionId }
            assertNotNull("La opción correcta debe existir tras el shuffle", correctOpt)
            assertTrue(correctOpt!!.text.isNotBlank())
        }
    }
}
