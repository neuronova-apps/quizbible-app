package com.neuronova.quizbible

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.neuronova.quizbible.data.local.AppThemeMode
import com.neuronova.quizbible.data.local.QuizBibleRuntimeLoader
import com.neuronova.quizbible.data.local.UserPreferencesRepository
import com.neuronova.quizbible.data.model.DifficultyFilter
import com.neuronova.quizbible.data.model.GameMode
import com.neuronova.quizbible.data.model.QuizQuestion
import com.neuronova.quizbible.data.repository.QuizBibleRepository
import com.neuronova.quizbible.ui.game.GameScreen
import com.neuronova.quizbible.ui.home.HomeScreen
import com.neuronova.quizbible.ui.home.ProgressScreen
import com.neuronova.quizbible.ui.home.SettingsScreen
import com.neuronova.quizbible.ui.mode.DifficultySelectionScreen
import com.neuronova.quizbible.ui.mode.ModeSelectionScreen
import com.neuronova.quizbible.ui.result.ResultScreen
import com.neuronova.quizbible.ui.theme.QuizBibleTheme

class MainActivity : ComponentActivity() {

    private val repository: QuizBibleRepository by lazy {
        val runtime = QuizBibleRuntimeLoader.loadFromAssets(applicationContext)
        QuizBibleRepository(runtime)
    }

    private val preferencesRepository: UserPreferencesRepository by lazy {
        UserPreferencesRepository(applicationContext)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            var settings by remember { mutableStateOf(preferencesRepository.getSettings()) }
            val navController = rememberNavController()

            // Active Match State
            var currentMatchQuestions by remember { mutableStateOf<List<QuizQuestion>>(emptyList()) }
            var currentMode by remember { mutableStateOf(GameMode.AMBOS_TESTAMENTOS) }
            var currentDifficulty by remember { mutableStateOf(DifficultyFilter.ALL) }
            var lastMatchResult by remember { mutableStateOf(Pair(0, 10)) }

            QuizBibleTheme(themeMode = settings.themeMode) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    NavHost(navController = navController, startDestination = "home") {
                        composable("home") {
                            HomeScreen(
                                onPlayClick = { navController.navigate("mode_selection") },
                                onProgressClick = { navController.navigate("progress") },
                                onSettingsClick = { navController.navigate("settings") }
                            )
                        }

                        composable("mode_selection") {
                            ModeSelectionScreen(
                                onModeSelected = { mode ->
                                    currentMode = mode
                                    navController.navigate("difficulty_selection")
                                },
                                onBackClick = { navController.popBackStack() }
                            )
                        }

                        composable("difficulty_selection") {
                            DifficultySelectionScreen(
                                mode = currentMode,
                                onDifficultySelected = { diff ->
                                    currentDifficulty = diff
                                    currentMatchQuestions = repository.createGameMatch(currentMode, diff, 10)
                                    navController.navigate("game")
                                },
                                onBackClick = { navController.popBackStack() }
                            )
                        }

                        composable("game") {
                            GameScreen(
                                questions = currentMatchQuestions,
                                mode = currentMode,
                                difficultyFilter = currentDifficulty,
                                onGameFinished = { correct, total ->
                                    lastMatchResult = Pair(correct, total)
                                    preferencesRepository.recordGameResult(total, correct)
                                    navController.navigate("result") {
                                        popUpTo("home")
                                    }
                                },
                                onQuitClick = { navController.navigate("home") { popUpTo("home") { inclusive = true } } }
                            )
                        }

                        composable("result") {
                            ResultScreen(
                                correctCount = lastMatchResult.first,
                                totalCount = lastMatchResult.second,
                                mode = currentMode,
                                difficultyFilter = currentDifficulty,
                                onPlayAgain = {
                                    currentMatchQuestions = repository.createGameMatch(currentMode, currentDifficulty, 10)
                                    navController.navigate("game") {
                                        popUpTo("home")
                                    }
                                },
                                onChangeMode = {
                                    navController.navigate("mode_selection") {
                                        popUpTo("home")
                                    }
                                },
                                onHomeClick = {
                                    navController.navigate("home") {
                                        popUpTo("home") { inclusive = true }
                                    }
                                }
                            )
                        }

                        composable("progress") {
                            ProgressScreen(
                                progress = preferencesRepository.getProgress(),
                                onBackClick = { navController.popBackStack() }
                            )
                        }

                        composable("settings") {
                            SettingsScreen(
                                settings = settings,
                                onThemeChanged = { newTheme ->
                                    preferencesRepository.updateThemeMode(newTheme)
                                    settings = settings.copy(themeMode = newTheme)
                                },
                                onTextScaleChanged = { newScale ->
                                    preferencesRepository.updateTextScale(newScale)
                                    settings = settings.copy(textScale = newScale)
                                },
                                onBackClick = { navController.popBackStack() }
                            )
                        }
                    }
                }
            }
        }
    }
}
