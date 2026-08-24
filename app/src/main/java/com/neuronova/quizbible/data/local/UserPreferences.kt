package com.neuronova.quizbible.data.local

import android.content.Context
import android.content.SharedPreferences

enum class AppThemeMode {
    LIGHT,
    DARK,
    HIGH_CONTRAST
}

data class UserProgress(
    val gamesPlayed: Int,
    val questionsAnswered: Int,
    val correctAnswers: Int,
    val bestScore: Int
) {
    val accuracyPercentage: Int
        get() = if (questionsAnswered > 0) (correctAnswers * 100) / questionsAnswered else 0
}

data class AppSettings(
    val themeMode: AppThemeMode = AppThemeMode.LIGHT,
    val textScale: Float = 1.0f,
    val language: String = "Español (RVR1960)"
)

class UserPreferencesRepository(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("quizbible_preferences", Context.MODE_PRIVATE)

    fun getProgress(): UserProgress {
        return UserProgress(
            gamesPlayed = prefs.getInt("games_played", 0),
            questionsAnswered = prefs.getInt("questions_answered", 0),
            correctAnswers = prefs.getInt("correct_answers", 0),
            bestScore = prefs.getInt("best_score", 0)
        )
    }

    fun recordGameResult(answered: Int, correct: Int) {
        val current = getProgress()
        val newGames = current.gamesPlayed + 1
        val newAnswered = current.questionsAnswered + answered
        val newCorrect = current.correctAnswers + correct
        val newBest = maxOf(current.bestScore, correct)

        prefs.edit()
            .putInt("games_played", newGames)
            .putInt("questions_answered", newAnswered)
            .putInt("correct_answers", newCorrect)
            .putInt("best_score", newBest)
            .apply()
    }

    fun getSettings(): AppSettings {
        val themeStr = prefs.getString("theme_mode", AppThemeMode.LIGHT.name) ?: AppThemeMode.LIGHT.name
        val themeMode = try { AppThemeMode.valueOf(themeStr) } catch (e: Exception) { AppThemeMode.LIGHT }
        val textScale = prefs.getFloat("text_scale", 1.0f)
        val language = prefs.getString("language", "Español (RVR1960)") ?: "Español (RVR1960)"

        return AppSettings(themeMode, textScale, language)
    }

    fun updateThemeMode(mode: AppThemeMode) {
        prefs.edit().putString("theme_mode", mode.name).apply()
    }

    fun updateTextScale(scale: Float) {
        prefs.edit().putFloat("text_scale", scale).apply()
    }
}
