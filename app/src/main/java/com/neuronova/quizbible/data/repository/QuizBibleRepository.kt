package com.neuronova.quizbible.data.repository

import com.neuronova.quizbible.data.model.AuditStatus
import com.neuronova.quizbible.data.model.Difficulty
import com.neuronova.quizbible.data.model.DifficultyFilter
import com.neuronova.quizbible.data.model.GameMode
import com.neuronova.quizbible.data.model.QuizOption
import com.neuronova.quizbible.data.model.QuizQuestion
import com.neuronova.quizbible.data.model.QuizRuntime
import kotlin.random.Random

class QuizBibleRepository(
    private val runtime: QuizRuntime
) {
    // Excluye automáticamente cualquier pregunta REQUIRES_CORRECTION (actualmente 0)
    private val playableQuestions: List<QuizQuestion> by lazy {
        runtime.questions.filter { it.auditStatus != AuditStatus.REQUIRES_CORRECTION }
    }

    fun getAllQuestions(): List<QuizQuestion> = playableQuestions

    fun getQuestionsByMode(mode: GameMode): List<QuizQuestion> {
        return playableQuestions.filter { mode.eligibleModeKey in it.eligibleModes }
    }

    fun getQuestions(mode: GameMode, difficultyFilter: DifficultyFilter): List<QuizQuestion> {
        val byMode = getQuestionsByMode(mode)
        val targetDiff = difficultyFilter.difficulty
        return if (targetDiff == null) {
            byMode
        } else {
            byMode.filter { it.difficulty == targetDiff }
        }
    }

    fun getQuestionsByBook(bookKeyOrName: String): List<QuizQuestion> {
        val query = bookKeyOrName.trim().lowercase()
        return playableQuestions.filter { it.book.trim().lowercase() == query }
    }

    fun getQuestionsByCategory(category: String): List<QuizQuestion> {
        return playableQuestions.filter { it.category == category }
    }

    fun createGameMatch(
        mode: GameMode,
        difficultyFilter: DifficultyFilter = DifficultyFilter.ALL,
        matchSize: Int = 10,
        random: Random = Random.Default
    ): List<QuizQuestion> {
        val eligible = getQuestions(mode, difficultyFilter)
        if (eligible.isEmpty()) {
            throw IllegalArgumentException(
                "No existen preguntas disponibles para el modo '${mode.title}' con dificultad '${difficultyFilter.displayName}'."
            )
        }

        val takeCount = minOf(matchSize, eligible.size)
        val selected = eligible.shuffled(random).take(takeCount)

        // Barajar opciones preservando option.id para validación
        return selected.map { q ->
            val shuffledOptions = q.options.shuffled(random)
            q.copy(options = shuffledOptions)
        }
    }
}
