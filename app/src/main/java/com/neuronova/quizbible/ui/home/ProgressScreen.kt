package com.neuronova.quizbible.ui.home

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neuronova.quizbible.data.local.UserProgress

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProgressScreen(
    progress: UserProgress,
    onBackClick: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Progreso y Estadísticas", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Atrás")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(text = "Rendimiento General", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    Spacer(modifier = Modifier.height(16.dp))

                    StatRow(title = "Partidas Jugadas", value = "${progress.gamesPlayed}")
                    Divider(modifier = Modifier.padding(vertical = 8.dp), color = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f))

                    StatRow(title = "Preguntas Respondidas", value = "${progress.questionsAnswered}")
                    Divider(modifier = Modifier.padding(vertical = 8.dp), color = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f))

                    StatRow(title = "Respuestas Correctas", value = "${progress.correctAnswers}")
                    Divider(modifier = Modifier.padding(vertical = 8.dp), color = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f))

                    StatRow(title = "Porcentaje de Acierto", value = "${progress.accuracyPercentage}%")
                    Divider(modifier = Modifier.padding(vertical = 8.dp), color = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f))

                    StatRow(title = "Mejor Puntuación", value = "${progress.bestScore} / 10")
                }
            }
        }
    }
}

@Composable
private fun StatRow(title: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = title, fontSize = 15.sp, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f))
        Text(text = value, fontSize = 17.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
    }
}
