package com.neuronova.quizbible.ui.result

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material.icons.filled.ViewList
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neuronova.quizbible.data.model.DifficultyFilter
import com.neuronova.quizbible.data.model.GameMode

@Composable
fun ResultScreen(
    correctCount: Int,
    totalCount: Int,
    mode: GameMode,
    difficultyFilter: DifficultyFilter,
    onPlayAgain: () -> Unit,
    onChangeMode: () -> Unit,
    onHomeClick: () -> Unit
) {
    val percentage = if (totalCount > 0) (correctCount * 100) / totalCount else 0
    val incorrectCount = totalCount - correctCount

    val (message, messageColor) = when {
        percentage >= 90 -> Pair("¡Excelente conocimiento bíblico!", MaterialTheme.colorScheme.primary)
        percentage >= 70 -> Pair("¡Muy buen trabajo!", MaterialTheme.colorScheme.primary)
        percentage >= 50 -> Pair("¡Buen esfuerzo, sigue estudiando!", MaterialTheme.colorScheme.secondary)
        else -> Pair("La Palabra de Dios es lámpara a tus pies. ¡Sigue aprendiendo!", MaterialTheme.colorScheme.onBackground)
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Header
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(top = 20.dp)
            ) {
                Text(
                    text = "PARTIDA COMPLETADA",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "${mode.title} • ${difficultyFilter.displayName}",
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f)
                )
            }

            // Score Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "$percentage%",
                        fontSize = 54.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "$correctCount de $totalCount correctas",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Divider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f))
                    Spacer(modifier = Modifier.height(16.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(text = "Correctas", fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                            Text(text = "$correctCount", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                        }
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(text = "Incorrectas", fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                            Text(text = "$incorrectCount", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.error)
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = message,
                        fontSize = 14.sp,
                        textAlign = TextAlign.Center,
                        fontWeight = FontWeight.Medium,
                        color = messageColor
                    )
                }
            }

            // Buttons
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Button(
                    onClick = onPlayAgain,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(54.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Icon(Icons.Default.Replay, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = "JUGAR DE NUEVO", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }

                OutlinedButton(
                    onClick = onChangeMode,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(54.dp),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Icon(Icons.Default.ViewList, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = "CAMBIAR MODO", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                }

                TextButton(
                    onClick = onHomeClick,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                ) {
                    Icon(Icons.Default.Home, contentDescription = null)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(text = "VOLVER AL INICIO", fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}
