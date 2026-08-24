package com.neuronova.quizbible.ui.game

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neuronova.quizbible.data.model.DifficultyFilter
import com.neuronova.quizbible.data.model.GameMode
import com.neuronova.quizbible.data.model.QuizOption
import com.neuronova.quizbible.data.model.QuizQuestion
import com.neuronova.quizbible.ui.theme.CorrectGreen
import com.neuronova.quizbible.ui.theme.IncorrectRed

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GameScreen(
    questions: List<QuizQuestion>,
    mode: GameMode,
    difficultyFilter: DifficultyFilter,
    onGameFinished: (correctCount: Int, totalCount: Int) -> Unit,
    onQuitClick: () -> Unit
) {
    var currentIndex by remember { mutableStateOf(0) }
    var selectedOptionId by remember { mutableStateOf<String?>(null) }
    var correctCount by remember { mutableStateOf(0) }

    val currentQuestion = questions.getOrNull(currentIndex)

    if (currentQuestion == null) {
        LaunchedEffect(Unit) {
            onGameFinished(correctCount, questions.size)
        }
        return
    }

    val isAnswered = selectedOptionId != null
    val isCorrect = selectedOptionId == currentQuestion.correctOptionId
    val isLastQuestion = currentIndex >= questions.size - 1

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Pregunta ${currentIndex + 1} de ${questions.size}",
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp
                    )
                },
                actions = {
                    TextButton(onClick = onQuitClick) {
                        Text("Salir", color = MaterialTheme.colorScheme.error)
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                // Progress indicator & Badges
                LinearProgressIndicator(
                    progress = (currentIndex + 1).toFloat() / questions.size,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(8.dp),
                    color = MaterialTheme.colorScheme.primary,
                    trackColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)
                )

                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    SuggestionChip(
                        onClick = {},
                        label = { Text(currentQuestion.difficulty.displayName, fontSize = 12.sp) }
                    )
                    SuggestionChip(
                        onClick = {},
                        label = { Text(currentQuestion.book, fontSize = 12.sp, fontWeight = FontWeight.SemiBold) }
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Prompt Card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Text(
                        text = currentQuestion.prompt,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        lineHeight = 28.sp,
                        modifier = Modifier.padding(20.dp),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                Spacer(modifier = Modifier.height(20.dp))

                // Options List
                currentQuestion.options.forEach { option ->
                    val isThisOptionSelected = selectedOptionId == option.id
                    val isThisOptionCorrect = currentQuestion.correctOptionId == option.id

                    val (containerColor, borderColor, contentColor) = when {
                        !isAnswered -> Triple(
                            MaterialTheme.colorScheme.surface,
                            MaterialTheme.colorScheme.outline.copy(alpha = 0.3f),
                            MaterialTheme.colorScheme.onSurface
                        )
                        isThisOptionCorrect -> Triple(
                            CorrectGreen.copy(alpha = 0.15f),
                            CorrectGreen,
                            CorrectGreen
                        )
                        isThisOptionSelected -> Triple(
                            IncorrectRed.copy(alpha = 0.15f),
                            IncorrectRed,
                            IncorrectRed
                        )
                        else -> Triple(
                            MaterialTheme.colorScheme.surface.copy(alpha = 0.5f),
                            MaterialTheme.colorScheme.outline.copy(alpha = 0.2f),
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                        )
                    }

                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 6.dp)
                            .clickable(enabled = !isAnswered) {
                                selectedOptionId = option.id
                                if (option.id == currentQuestion.correctOptionId) {
                                    correctCount++
                                }
                            },
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = containerColor),
                        border = BorderStroke(if (isAnswered && (isThisOptionCorrect || isThisOptionSelected)) 2.dp else 1.dp, borderColor)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = option.text,
                                fontSize = 16.sp,
                                fontWeight = if (isAnswered && isThisOptionCorrect) FontWeight.Bold else FontWeight.Medium,
                                color = contentColor,
                                modifier = Modifier.weight(1f)
                            )
                            if (isAnswered) {
                                if (isThisOptionCorrect) {
                                    Icon(Icons.Default.CheckCircle, contentDescription = "Correcto", tint = CorrectGreen)
                                } else if (isThisOptionSelected) {
                                    Icon(Icons.Default.Close, contentDescription = "Incorrecto", tint = IncorrectRed)
                                }
                            }
                        }
                    }
                }

                // Feedback & Explanation (ONLY AFTER ANSWERING)
                if (isAnswered) {
                    Spacer(modifier = Modifier.height(16.dp))

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isCorrect) CorrectGreen.copy(alpha = 0.1f) else IncorrectRed.copy(alpha = 0.1f)
                        )
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(
                                text = if (isCorrect) "¡CORRECTO!" else "INCORRECTO",
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                                color = if (isCorrect) CorrectGreen else IncorrectRed
                            )
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = currentQuestion.explanation,
                                fontSize = 14.sp,
                                lineHeight = 20.sp,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            // Reference display ONLY visible after answering
                            Text(
                                text = "Referencia: ${currentQuestion.referenceDisplay} (RVR1960)",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                }
            }

            // Bottom Action: Siguiente / Ver Resultados
            if (isAnswered) {
                Column(modifier = Modifier.padding(vertical = 20.dp)) {
                    Button(
                        onClick = {
                            if (isLastQuestion) {
                                onGameFinished(correctCount, questions.size)
                            } else {
                                currentIndex++
                                selectedOptionId = null
                            }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                    ) {
                        Text(
                            text = if (isLastQuestion) "VER RESULTADOS" else "SIGUIENTE PREGUNTA",
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            } else {
                Spacer(modifier = Modifier.height(20.dp))
            }
        }
    }
}
